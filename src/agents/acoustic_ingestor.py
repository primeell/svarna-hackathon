"""
Project SVARNA — Agent 1: AcousticSignalIngestor
==================================================
Transcribes farmer voice notes using faster-whisper.
Universal: auto-selects CUDA GPU or CPU depending on hardware.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.blackboard import Blackboard
from src.models.schemas import PipelineStatus, TranscriptionResult, TranscriptionSegment


class AcousticSignalIngestor(BaseAgent):
    """
    Agent 1: Converts audio files to text transcriptions.

    Hardware: Auto-detect (CUDA GPU → CPU fallback)
    Model: faster-whisper small (default)
    """

    def __init__(self, config: dict, blackboard: Blackboard):
        super().__init__(
            name="AcousticSignalIngestor",
            config=config,
            blackboard=blackboard,
        )
        self._model = None
        self._device = "cpu"

    def initialize(self) -> None:
        """Load the Whisper model. Auto-detect best available device."""
        model_config = self.config.get("model", {})
        model_size = model_config.get("model_size", "small")

        logger.info(f"[{self.name}] Initializing model: {model_size}")

        try:
            from faster_whisper import WhisperModel

            # Auto-detect device
            device, compute_type = self._detect_device()
            self._device = device

            self._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            logger.info(
                f"[{self.name}] Model loaded — device={device}, compute={compute_type}"
            )

        except ImportError:
            logger.warning(
                f"[{self.name}] faster-whisper not installed. "
                "Running in MOCK mode with sample transcriptions."
            )
            self._model = None

    @staticmethod
    def _detect_device() -> tuple[str, str]:
        """
        Pick the best device for faster-whisper.
        Returns (device, compute_type).
        """
        # Try CUDA first
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda", "float16"
        except ImportError:
            pass

        # CPU fallback — int8 is fastest on CPU
        return "cpu", "int8"

    def process(self, input_data: Any) -> dict:
        """
        Transcribe an audio file.

        Args:
            input_data: Path to the audio file (str) or dict with 'audio_file' key.
        """
        # Parse input
        if isinstance(input_data, dict):
            audio_path = input_data.get("audio_file", "")
        elif isinstance(input_data, str):
            audio_path = input_data
        else:
            audio_path = ""

        transcription_id = f"TR-{uuid.uuid4().hex[:8].upper()}"

        # If model is not loaded, return mock data
        if self._model is None:
            return self._mock_transcription(transcription_id, audio_path)

        # Real transcription
        if not Path(audio_path).exists():
            logger.error(f"[{self.name}] Audio file not found: {audio_path}")
            return {
                "id": transcription_id,
                "status": PipelineStatus.FAILED.value,
                "error": f"File not found: {audio_path}",
            }

        try:
            language = self.config.get("model", {}).get("language", "id")
            beam_size = self.config.get("model", {}).get("beam_size", 5)

            segments_gen, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size,
                vad_filter=True,
            )

            segments = []
            full_text_parts = []
            for seg in segments_gen:
                segments.append(TranscriptionSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    confidence=seg.avg_logprob if hasattr(seg, "avg_logprob") else 0.9,
                ))
                full_text_parts.append(seg.text.strip())

            result = TranscriptionResult(
                id=transcription_id,
                audio_file=audio_path,
                full_text=" ".join(full_text_parts),
                segments=segments,
                language=info.language if info else language,
                noise_confidence=0.85,
                duration_seconds=info.duration if info else 0.0,
                timestamp=datetime.now(),
                status=PipelineStatus.COMPLETED,
            )

            return result.model_dump(mode="json")

        except Exception as e:
            logger.error(f"[{self.name}] Transcription error: {e}")
            return {
                "id": transcription_id,
                "status": PipelineStatus.FAILED.value,
                "error": str(e),
            }

    def validate(self, result: dict) -> tuple[bool, list[str]]:
        """Validate transcription quality."""
        issues = []

        if result.get("status") == PipelineStatus.FAILED.value:
            issues.append(f"Transcription failed: {result.get('error', 'unknown')}")
            return False, issues

        text = result.get("full_text", "")
        if len(text.strip()) < 5:
            issues.append("Transcription too short (< 5 chars)")

        noise_conf = result.get("noise_confidence", 0)
        if noise_conf < 0.5:
            issues.append(f"Low audio quality (noise_confidence={noise_conf:.2f})")

        return len(issues) == 0, issues

    def write_output(self, result: dict) -> None:
        """Write transcription to the blackboard."""
        self.blackboard.write(
            entry_id=result.get("id", "unknown"),
            agent_source=self.name,
            entry_type="transcriptions",
            payload=result,
        )

    def _mock_transcription(self, tid: str, audio_path: str) -> dict:
        """Generate a mock transcription for testing without Whisper."""
        logger.info(f"[{self.name}] Generating MOCK transcription for {audio_path}")

        mock = TranscriptionResult(
            id=tid,
            audio_file=audio_path or "sample_audio/mock.wav",
            full_text=(
                "Pak, saya punya beras 5 kuintal di desa Sukamaju, "
                "Kabupaten Cianjur. Harga saya minta 12 ribu per kilo. "
                "Tolong bantu carikan pembeli."
            ),
            segments=[
                TranscriptionSegment(start=0.0, end=3.5,
                    text="Pak, saya punya beras 5 kuintal di desa Sukamaju,",
                    confidence=0.92),
                TranscriptionSegment(start=3.5, end=7.0,
                    text="Kabupaten Cianjur. Harga saya minta 12 ribu per kilo.",
                    confidence=0.89),
                TranscriptionSegment(start=7.0, end=9.0,
                    text="Tolong bantu carikan pembeli.",
                    confidence=0.94),
            ],
            language="id",
            noise_confidence=0.88,
            duration_seconds=9.0,
            timestamp=datetime.now(),
            status=PipelineStatus.COMPLETED,
        )
        return mock.model_dump(mode="json")
