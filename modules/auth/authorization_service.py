from __future__ import annotations

from dataclasses import replace

from modules.domain.models import AppUser
from modules.services.user_service import find_user_by_email, list_active_users, parse_whitelist_dataframe
from modules.storage.whitelist_repository import WhitelistRepository


class AuthorizationService:
    """Authorize authenticated identities against the whitelist worksheet."""

    def __init__(self, whitelist_repository: WhitelistRepository) -> None:
        self._whitelist_repository = whitelist_repository

    def load_users(self) -> tuple[list[AppUser], list[str]]:
        """Load all whitelist entries."""

        frame = self._whitelist_repository.load_frame()
        return parse_whitelist_dataframe(frame)

    def authorize(self, email: str | None, *, fallback_name: str | None = None) -> AppUser | None:
        """Return the active authorized user that matches the provided email."""

        users, _ = self.load_users()
        user = find_user_by_email(users, email)
        if user is None or not user.is_active:
            return None
        if fallback_name and not user.name:
            return replace(user, name=fallback_name)
        return user

    def list_active_users(self) -> list[AppUser]:
        """Return all active whitelist users."""

        users, _ = self.load_users()
        return list_active_users(users)
