"""
Project SVARNA — Agent 2: SemanticDataParser
===============================================
Extracts structured entities from farmer transcriptions via local LLM (Ollama).
Falls back to regex-based extraction if Ollama is unavailable.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.blackboard import Blackboard
from src.core.unit_converter import UnitConverter
from src.models.schemas import FarmerReport, GeoLocation, PipelineStatus


# Known Indonesian commodity terms
COMMODITY_KEYWORDS = [
    "beras", "cabai", "cabai rawit", "cabai merah", "tomat",
    "bawang merah", "bawang putih", "jagung", "kedelai",
    "gula pasir", "minyak goreng", "telur", "daging sapi",
    "daging ayam", "pisang", "kentang", "wortel", "bayam",
    "kangkung", "terong",
]

# Known unit terms
UNIT_KEYWORDS = [
    "kg", "kilo", "kilogram", "kuintal", "ton",
    "karung", "peti", "ikat", "sisir", "tandan",
    "butir", "ekor", "liter",
]


class SemanticDataParser(BaseAgent):
    """
    Agent 2: Converts raw transcriptions into structured FarmerReport entities.

    Hardware: Mobile/Edge MCU (Ollama/CTranslate2) → regex fallback
    Model: qwen2.5:0.5b via Ollama
    """

    def __init__(self, config: dict, blackboard: Blackboard):
        super().__init__(
            name="SemanticDataParser",
            config=config,
            blackboard=blackboard,
        )
        self._ollama_available = False
        self._unit_converter = UnitConverter()

    def initialize(self) -> None:
        """Check Ollama availability."""
        model_config = self.config.get("model", {})
        model_name = model_config.get("model_name", "qwen2.5:0.5b")

        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                self._ollama_available = True
                logger.info(f"[{self.name}] Ollama available. Using model: {model_name}")
            else:
                logger.warning(f"[{self.name}] Ollama not responding. Using regex fallback.")
        except Exception:
            logger.warning(f"[{self.name}] Ollama not available. Using regex fallback.")

    def process(self, input_data: Any) -> dict:
        """
        Extract structured entities from a transcription.
        
        Args:
            input_data: TranscriptionResult dict or None (reads from blackboard).
        """
        # Get transcription text
        if input_data and isinstance(input_data, dict):
            text = input_data.get("full_text", "")
            transcription_id = input_data.get("id", "unknown")
        else:
            latest = self.blackboard.read_latest("transcriptions")
            if not latest:
                return {"status": PipelineStatus.FAILED.value, "error": "No transcription found"}
            text = latest["payload"].get("full_text", "")
            transcription_id = latest["payload"].get("id", "unknown")

        report_id = f"FR-{uuid.uuid4().hex[:8].upper()}"

        if self._ollama_available:
            return self._extract_with_llm(report_id, transcription_id, text)
        else:
            return self._extract_with_regex(report_id, transcription_id, text)

    def _extract_with_llm(self, report_id: str, transcription_id: str, text: str) -> dict:
        """Use Ollama LLM for entity extraction."""
        model_config = self.config.get("model", {})
        model_name = model_config.get("model_name", "qwen2.5:0.5b")

        prompt = f"""Extract structured agricultural data from this Indonesian farmer's voice note transcription.

TRANSCRIPTION: "{text}"

Return ONLY valid JSON with these fields:
{{
    "commodity": "commodity name in Indonesian",
    "volume": numeric_value,
    "local_unit": "unit name",
    "asking_price": numeric_price_in_idr,
    "village_name": "village name or null",
    "district": "district/kabupaten name or null",
    "province": "province name or null",
    "latitude": numeric_or_null,
    "longitude": numeric_or_null,
    "confidence": 0.0_to_1.0
}}"""

        try:
            import httpx
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=60,
            )

            if response.status_code == 200:
                raw_response = response.json().get("response", "{}")
                parsed = json.loads(raw_response)
                return self._build_report(report_id, transcription_id, text, parsed)

        except Exception as e:
            logger.warning(f"[{self.name}] LLM extraction failed: {e}. Falling back to regex.")

        return self._extract_with_regex(report_id, transcription_id, text)

    def _extract_with_regex(self, report_id: str, transcription_id: str, text: str) -> dict:
        """Fallback: rule-based entity extraction using regex patterns."""
        logger.info(f"[{self.name}] Using regex extraction for: {text[:80]}...")

        text_lower = text.lower()

        # Extract commodity
        commodity = "unknown"
        for kw in COMMODITY_KEYWORDS:
            if kw in text_lower:
                commodity = kw
                break

        # Extract volume (number before a unit keyword)
        volume = 0.0
        local_unit = "kg"
        for unit in UNIT_KEYWORDS:
            pattern = rf"(\d+(?:[.,]\d+)?)\s*{unit}"
            match = re.search(pattern, text_lower)
            if match:
                volume = float(match.group(1).replace(",", "."))
                local_unit = unit
                break

        # Extract price (look for "ribu" = thousands)
        asking_price = 0.0
        price_match = re.search(r"(\d+(?:[.,]\d+)?)\s*ribu", text_lower)
        if price_match:
            asking_price = float(price_match.group(1).replace(",", ".")) * 1000
        else:
            price_match = re.search(r"(?:harga|Rp|rp)\s*(\d+(?:[.,]\d+)?)", text_lower)
            if price_match:
                asking_price = float(price_match.group(1).replace(",", "."))

        # Extract location
        village_name = None
        district = None
        desa_match = re.search(r"desa\s+(\w+)", text_lower)
        if desa_match:
            village_name = desa_match.group(1).title()
        kab_match = re.search(r"(?:kabupaten|kab\.?)\s+(\w+)", text_lower)
        if kab_match:
            district = kab_match.group(1).title()

        parsed = {
            "commodity": commodity,
            "volume": volume,
            "local_unit": local_unit,
            "asking_price": asking_price,
            "village_name": village_name,
            "district": district,
            "province": None,
            "latitude": -6.75,   # Default: central Java
            "longitude": 107.0,
            "confidence": 0.72,  # Lower confidence for regex
        }

        return self._build_report(report_id, transcription_id, text, parsed)

    def _build_report(
        self, report_id: str, transcription_id: str, raw_text: str, parsed: dict
    ) -> dict:
        """Construct a FarmerReport from parsed data."""
        commodity = parsed.get("commodity", "unknown")
        volume = parsed.get("volume", 0.0) or 1.0
        local_unit = parsed.get("local_unit", "kg")
        asking_price = parsed.get("asking_price", 0.0)

        # Convert to KG
        try:
            volume_kg = self._unit_converter.to_kg(volume, local_unit, commodity)
        except ValueError:
            volume_kg = volume  # Assume KG if unit unknown

        # Price per KG
        price_per_kg = asking_price / volume_kg if volume_kg > 0 else 0.0

        report = FarmerReport(
            id=report_id,
            transcription_id=transcription_id,
            commodity=commodity,
            volume=volume,
            local_unit=local_unit,
            volume_kg=volume_kg,
            asking_price=asking_price,
            price_per_kg=price_per_kg,
            geo_location=GeoLocation(
                latitude=parsed.get("latitude", -6.75),
                longitude=parsed.get("longitude", 107.0),
                village_name=parsed.get("village_name"),
                district=parsed.get("district"),
                province=parsed.get("province"),
            ),
            extraction_confidence=parsed.get("confidence", 0.5),
            timestamp=datetime.now(),
            status=PipelineStatus.COMPLETED,
            raw_text=raw_text,
        )

        return report.model_dump(mode="json")

    def validate(self, result: dict) -> tuple[bool, list[str]]:
        """Validate extraction quality."""
        issues = []

        if result.get("status") == PipelineStatus.FAILED.value:
            issues.append(f"Extraction failed: {result.get('error', 'unknown')}")
            return False, issues

        confidence = result.get("extraction_confidence", 0)
        threshold = self.config.get("confidence_threshold", 0.85)

        if confidence < threshold:
            issues.append(
                f"Low confidence ({confidence:.2f} < {threshold}). "
                "May need clarification."
            )

        if result.get("commodity") == "unknown":
            issues.append("Commodity not identified")

        if result.get("volume_kg", 0) <= 0:
            issues.append("Volume is zero or negative")

        return len(issues) == 0, issues

    def write_output(self, result: dict) -> None:
        """Write parsed report to the blackboard."""
        self.blackboard.write(
            entry_id=result.get("id", "unknown"),
            agent_source=self.name,
            entry_type="parsed_reports",
            payload=result,
        )
