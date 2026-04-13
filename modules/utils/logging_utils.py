from __future__ import annotations

import ast
import json
import logging
import sys
import textwrap
from pathlib import Path
from typing import Any

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

    formatter = _StructuredLogFormatter(datefmt="%Y-%m-%d %H:%M:%S")

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


class _StructuredLogFormatter(logging.Formatter):
    """Render compact prefixes plus readable multi-line structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        headline, fields = _split_log_message(message)
        timestamp = self.formatTime(record, self.datefmt)
        prefix = f"[{timestamp}][{record.levelname}][{record.name}]"
        lines = _format_headline(prefix, headline)
        if fields:
            lines.extend(_format_fields(fields))

        if record.exc_info:
            lines.append(_indent_block(self.formatException(record.exc_info), spaces=2))
        if record.stack_info:
            lines.append(_indent_block(self.formatStack(record.stack_info), spaces=2))
        return "\n".join(lines)


def _format_headline(prefix: str, headline: str) -> list[str]:
    message_lines = headline.splitlines() or [""]
    formatted = [f"{prefix} {message_lines[0]}".rstrip()]
    formatted.extend(_indent_block(line, spaces=2) for line in message_lines[1:])
    return formatted


def _split_log_message(message: str) -> tuple[str, list[tuple[str, str]]]:
    segments = message.split(" | ")
    headline = segments[0]
    fields: list[tuple[str, str]] = []
    trailing_segments: list[str] = []

    for segment in segments[1:]:
        if "=" not in segment:
            trailing_segments.append(segment)
            continue
        key, value = segment.split("=", 1)
        fields.append((key.strip(), value.strip()))

    if trailing_segments:
        headline = " | ".join([headline, *trailing_segments])
    return headline, fields


def _format_fields(fields: list[tuple[str, str]]) -> list[str]:
    key_width = max(len(key) for key, _ in fields)
    lines: list[str] = []
    for key, raw_value in fields:
        rendered_value = _render_field_value(key, raw_value)
        if "\n" not in rendered_value:
            lines.append(f"  {key.ljust(key_width)}: {rendered_value}")
            continue

        lines.append(f"  {key.ljust(key_width)}:")
        lines.extend(_indent_block(line, spaces=4) for line in rendered_value.splitlines())
    return lines


def _render_field_value(key: str, raw_value: str) -> str:
    if key == "sql":
        return _normalize_sql(raw_value)

    structured_value = _coerce_structured_value(raw_value)
    if isinstance(structured_value, (dict, list)):
        if not structured_value:
            return json.dumps(structured_value, ensure_ascii=False)
        return json.dumps(structured_value, ensure_ascii=False, indent=2, default=str)
    return raw_value


def _coerce_structured_value(raw_value: str) -> Any:
    stripped = raw_value.strip()
    if not stripped:
        return raw_value
    if not (
        (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith("[") and stripped.endswith("]"))
    ):
        return raw_value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return raw_value


def _normalize_sql(raw_sql: str) -> str:
    lines = [
        line.rstrip()
        for line in textwrap.dedent(raw_sql).strip().splitlines()
        if line.strip()
    ]
    if len(lines) <= 1:
        return "\n".join(lines)

    trailing_indent = min(
        (
            len(line) - len(line.lstrip())
            for line in lines[1:]
            if line.strip()
        ),
        default=0,
    )
    if trailing_indent <= 0:
        return "\n".join(lines)

    normalized_tail = [line[trailing_indent:] for line in lines[1:]]
    return "\n".join([lines[0], *normalized_tail])


def _indent_block(value: str, *, spaces: int) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else indent for line in value.splitlines())
