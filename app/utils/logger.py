from __future__ import annotations

import logging
from pathlib import Path

from app.config import AppConfig


def build_logger(config: AppConfig) -> logging.Logger:
    logger = logging.getLogger(config.app_name)
    if logger.handlers:
        return logger

    logger.setLevel(config.log_level.upper())

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_path = Path(config.log_dir) / "jarvis.log"
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger

