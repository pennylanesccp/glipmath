from __future__ import annotations

from secrets import randbelow
from typing import Any

GENERATED_QUESTION_ID_MIN = 1_000_000_000_000
GENERATED_QUESTION_ID_MAX = 9_000_000_000_000_000


def resolve_seed_question_id(
    value: Any,
    *,
    field_name: str,
    seen_question_ids: set[int],
) -> int:
    """Return an explicit question ID or generate a unique random one."""

    id_question = _optional_int(value, field_name)
    if id_question is None:
        id_question = generate_random_question_id(seen_question_ids)

    if id_question in seen_question_ids:
        raise ValueError(f"Duplicate id_question in questions: {id_question}")
    seen_question_ids.add(id_question)
    return id_question


def generate_random_question_id(seen_question_ids: set[int]) -> int:
    """Generate one high-range positive BigQuery INT64 question ID."""

    range_size = GENERATED_QUESTION_ID_MAX - GENERATED_QUESTION_ID_MIN + 1
    while True:
        id_question = GENERATED_QUESTION_ID_MIN + randbelow(range_size)
        if id_question not in seen_question_ids:
            return id_question


def _optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
