"""
Project SVARNA — Universal Hardware Detection
================================================
Auto-detects the best compute backend: CUDA → DirectML → CoreML → CPU.
Works on any device without requiring OpenVINO.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""
    cpu_name: str
    cpu_cores: int
    best_device: str             # "cuda", "directml", "mps", "cpu"
    best_compute_type: str       # "float16", "int8", etc.
    gpu_name: Optional[str]
    has_gpu: bool
    ollama_available: bool
    os_name: str


def detect_hardware() -> HardwareProfile:
    """Detect available hardware accelerators (universal, no OpenVINO needed)."""

    cpu_name = platform.processor() or "Unknown"
    cpu_cores = os.cpu_count() or 1
    os_name = platform.system()

    # Determine best device
    best_device, best_compute_type, gpu_name = _detect_best_device()
    has_gpu = best_device != "cpu"

    # Check for Ollama (LLM inference)
    ollama_available = _check_ollama()

    profile = HardwareProfile(
        cpu_name=cpu_name,
        cpu_cores=cpu_cores,
        best_device=best_device,
        best_compute_type=best_compute_type,
        gpu_name=gpu_name,
        has_gpu=has_gpu,
        ollama_available=ollama_available,
        os_name=os_name,
    )

    logger.info(f"Hardware profile: device={best_device}, compute={best_compute_type}, gpu={gpu_name}")
    return profile


def _detect_best_device() -> tuple[str, str, Optional[str]]:
    """
    Auto-detect the best compute device in priority order:
      1. CUDA (NVIDIA GPU)
      2. DirectML (Windows, any GPU)
      3. MPS (Apple Silicon)
      4. CPU (universal fallback)

    Returns: (device, compute_type, gpu_name)
    """

    # 1. Check CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA GPU detected: {gpu_name}")
            return "cuda", "float16", gpu_name
    except ImportError:
        pass

    # 2. Check Apple MPS (macOS Apple Silicon)
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Apple MPS backend detected")
            return "mps", "float16", "Apple Silicon"
    except (ImportError, AttributeError):
        pass

    # 3. Check DirectML (Windows, any GPU)
    if platform.system() == "Windows":
        try:
            import torch_directml  # noqa: F401
            logger.info("DirectML backend detected")
            gpu_name = _detect_gpu_name_windows()
            return "directml", "float16", gpu_name
        except ImportError:
            pass

    # 4. Fallback: CPU
    logger.info("No GPU acceleration found. Using CPU")
    return "cpu", "int8", None


def _detect_gpu_name_windows() -> Optional[str]:
    """Detect GPU name on Windows via WMIC."""
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = [
                l.strip() for l in result.stdout.splitlines()
                if l.strip() and l.strip().lower() != "name"
            ]
            return lines[0] if lines else None
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _check_ollama() -> bool:
    """Check if Ollama is accessible."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
