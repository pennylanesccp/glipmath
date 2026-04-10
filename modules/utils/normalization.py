from __future__ import annotations

import re
import unicodedata
from typing import Any

TRUE_VALUES = {"1", "true", "t", "yes", "y", "sim", "s"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "nao"}
_TAXONOMY_SEPARATOR_PATTERN = re.compile(r"[_-]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_email(value: str | None) -> str:
    """Normalize an email address for matching."""

    return (value or "").strip().lower()


def clean_optional_text(value: Any) -> str | None:
    """Return a stripped text value or None when blank."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def strip_accents(value: str) -> str:
    """Return one string without accent/diacritic marks."""

    normalized = unicodedata.normalize("NFD", value)
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )


def normalize_taxonomy_value(value: Any) -> str | None:
    """Return one canonical subject/topic key for storage and filtering."""

    text = clean_optional_text(value)
    if not text:
        return None

    normalized = strip_accents(text)
    normalized = _TAXONOMY_SEPARATOR_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    normalized = normalized.strip().lower()
    return normalized or None


def coerce_bool(value: Any, *, default: bool) -> bool:
    """Interpret common boolean-like values."""

    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if not normalized:
        return default
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default
