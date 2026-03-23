from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from modules.domain.models import User
from modules.services.user_service import build_user_from_access_entry, parse_user_access_dataframe
from modules.utils.normalization import normalize_email

if TYPE_CHECKING:
    from modules.storage.user_access_repository import UserAccessRepository


@dataclass(slots=True)
class AuthorizationService:
    """Resolve the authenticated app user from BigQuery access policy."""

    user_access_repository: "UserAccessRepository"

    def authorize(self, email: str | None, *, fallback_name: str | None = None) -> User | None:
        """Return the authorized user or None when no active access row exists."""

        normalized_email = normalize_email(email)
        if not normalized_email:
            return None

        access_frame = self.user_access_repository.load_active_user_frame(normalized_email)
        access_entries, _issues = parse_user_access_dataframe(access_frame)
        active_entries = [entry for entry in access_entries if entry.is_active]
        if not active_entries:
            return None
        return build_user_from_access_entry(active_entries[0], fallback_name=fallback_name)
