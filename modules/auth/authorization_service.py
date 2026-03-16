from __future__ import annotations

from modules.domain.models import User
from modules.services.user_service import build_user


class AuthorizationService:
    """Keep a lightweight authorization abstraction for future policy checks."""

    def authorize(self, email: str | None, *, fallback_name: str | None = None) -> User | None:
        """Return the authenticated user for the current beta model.

        Access control is externalized to Google OAuth app configuration and test users
        for this MVP. The app only requires a valid authenticated email.
        """

        return build_user(email, fallback_name=fallback_name)
