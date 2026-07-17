"""Application logging helpers."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .config import LOG_DIR


def setup_logging(log_dir: Path = LOG_DIR) -> logging.Logger:
    """Configure and return the app logger."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("local_pdf_converter")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

