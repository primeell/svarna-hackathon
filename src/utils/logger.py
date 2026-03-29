"""
Project SVARNA — Structured Logger
====================================
"""

import sys
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "logs/svarna.log") -> None:
    """Configure loguru for the project."""
    logger.remove()  # Remove default handler

    # Console output with color
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File output
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    logger.info(f"Logger configured: level={log_level}, file={log_file}")
