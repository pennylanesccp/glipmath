from __future__ import annotations

from uuid import uuid4


def generate_answer_id() -> str:
    """Generate a collision-resistant answer identifier for append-only events."""

    return uuid4().hex
