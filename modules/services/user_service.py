from __future__ import annotations

from modules.domain.models import User
from modules.utils.normalization import clean_optional_text, normalize_email


def build_user(email: str | None, *, fallback_name: str | None = None) -> User | None:
    """Build a normalized app user from the authenticated identity."""

    normalized_email = normalize_email(email)
    if not normalized_email:
        return None
    return User(
        email=normalized_email,
        name=clean_optional_text(fallback_name),
    )
