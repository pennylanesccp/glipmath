from __future__ import annotations

from collections.abc import Iterable


def next_numeric_id(existing_ids: Iterable[int]) -> int:
    """Return the next positive integer after the current maximum."""

    return max((value for value in existing_ids if value > 0), default=0) + 1
