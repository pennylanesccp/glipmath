from __future__ import annotations

from typing import Any

from modules.utils.normalization import clean_optional_text, strip_accents

DIFFICULTY_OPTIONS: tuple[tuple[int, str], ...] = (
    (1, "1. Básico"),
    (2, "2. Fácil"),
    (3, "3. Médio"),
    (4, "4. Difícil"),
    (5, "5. Avançado"),
)
DIFFICULTY_LABEL_BY_VALUE = {
    value: label
    for value, label in DIFFICULTY_OPTIONS
}
_DIFFICULTY_ALIAS_BY_KEY = {
    "1": 1,
    "1_basico": 1,
    "basico": 1,
    "basic": 1,
    "2": 2,
    "2_facil": 2,
    "facil": 2,
    "easy": 2,
    "desafio_leve": 2,
    "light_challenge": 2,
    "3": 3,
    "3_medio": 3,
    "medio": 3,
    "media": 3,
    "medium": 3,
    "4": 4,
    "4_dificil": 4,
    "dificil": 4,
    "difficult": 4,
    "hard": 4,
    "5": 5,
    "5_avancado": 5,
    "avancado": 5,
    "advanced": 5,
}


def normalize_difficulty_value(value: Any) -> int | None:
    """Normalize one difficulty value into the canonical 1-5 scale."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value in DIFFICULTY_LABEL_BY_VALUE else None

    text = clean_optional_text(value)
    if text is None:
        return None

    normalized_key = _difficulty_key(text)
    parsed_value = _DIFFICULTY_ALIAS_BY_KEY.get(normalized_key)
    if parsed_value is not None:
        return parsed_value

    if normalized_key.isdigit():
        numeric_value = int(normalized_key)
        return numeric_value if numeric_value in DIFFICULTY_LABEL_BY_VALUE else None

    prefix = normalized_key.split("_", 1)[0]
    if prefix.isdigit():
        numeric_value = int(prefix)
        return numeric_value if numeric_value in DIFFICULTY_LABEL_BY_VALUE else None

    return None


def require_difficulty_value(value: Any, field_name: str) -> int:
    """Return a canonical difficulty or raise a validation error."""

    parsed_value = normalize_difficulty_value(value)
    if parsed_value is None:
        raise ValueError(f"{field_name} must be a difficulty from 1 to 5.")
    return parsed_value


def format_difficulty_label(value: Any) -> str:
    """Return the friendly label for one normalized difficulty value."""

    normalized_value = normalize_difficulty_value(value)
    if normalized_value is None:
        return ""
    return DIFFICULTY_LABEL_BY_VALUE.get(normalized_value, str(normalized_value))


def _difficulty_key(value: str) -> str:
    normalized = strip_accents(value)
    normalized = normalized.strip().lower()
    for separator in ("-", " ", "."):
        normalized = normalized.replace(separator, "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")
