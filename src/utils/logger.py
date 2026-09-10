"""Logging helpers for EcoRiskAI scripts."""

import logging
import sys


def setup_logger(name: str = "EcoRiskAI", level: int = logging.INFO) -> logging.Logger:
    """Create a console logger with a consistent format."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
