from __future__ import annotations

import logging
import sys
from pathlib import Path

APP_LOGGER_NAME = "glipmath"
_CONFIGURED_SIGNATURE: tuple[int, str | None] | None = None


def configure_logging(
    *,
    level: str | int = logging.INFO,
    log_file: Path | None = None,
) -> logging.Logger:
    """Configure the application logger for console and optional file output."""

    global _CONFIGURED_SIGNATURE

    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.propagate = False
    configured_level = _coerce_level(level)
    configured_log_file = str(log_file) if log_file is not None else None
    signature = (configured_level, configured_log_file)

    if _CONFIGURED_SIGNATURE == signature and logger.handlers:
        logger.setLevel(configured_level)
        return logger

    logger.setLevel(configured_level)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logger.level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logger.level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.debug(
        "Logging configured | level=%s | log_file=%s",
        logging.getLevelName(logger.level),
        configured_log_file or "<none>",
    )
    _CONFIGURED_SIGNATURE = signature
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for the application."""

    return logging.getLogger(APP_LOGGER_NAME).getChild(name)


def _coerce_level(value: str | int) -> int:
    if isinstance(value, int):
        return value
    normalized = str(value).strip().upper()
    return getattr(logging, normalized, logging.INFO)
