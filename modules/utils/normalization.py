from __future__ import annotations

from typing import Any

TRUE_VALUES = {"1", "true", "t", "yes", "y", "sim", "s"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "nao"}


def normalize_email(value: str | None) -> str:
    """Normalize an email address for matching."""

    return (value or "").strip().lower()


def normalize_choice(value: str | None) -> str:
    """Normalize a multiple-choice label to a single uppercase letter."""

    normalized = (value or "").strip().upper()
    return normalized[:1] if normalized else ""


def clean_optional_text(value: Any) -> str | None:
    """Return a stripped text value or None when blank."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
