from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class WorksheetNames:
    """Worksheet names used by the application."""

    question_bank: str = "question_bank"
    whitelist: str = "whitelist"
    answers: str = "answers"


@dataclass(frozen=True, slots=True)
class GoogleSheetSettings:
    """Google Sheets connection settings."""

    spreadsheet_id: str | None
    spreadsheet_url: str | None
    retry_attempts: int = 3


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """OIDC-related settings read from Streamlit secrets."""

    redirect_uri: str | None
    cookie_secret: str | None
    client_id: str | None
    client_secret: str | None
    server_metadata_url: str | None

    @property
    def is_configured(self) -> bool:
        """Return whether the minimum OIDC settings are present."""

        return all(
            [
                self.redirect_uri,
                self.cookie_secret,
                self.client_id,
                self.client_secret,
                self.server_metadata_url,
            ]
        )


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Top-level application settings."""

    app_name: str
    environment: str
    timezone: str
    storage_backend: str
    app_version: str
    google_sheet: GoogleSheetSettings
    worksheets: WorksheetNames
    local_csv_base_dir: Path
    auth: AuthSettings
    service_account_info: dict[str, str] | None


def load_settings(
    secrets: Mapping[str, Any] | None = None,
    *,
    base_dir: Path | None = None,
) -> AppSettings:
    """Load application settings from Streamlit secrets or a supplied mapping."""

    secrets_dict = _to_plain_dict(secrets or _load_streamlit_secrets())
    resolved_base_dir = (base_dir or Path.cwd()).resolve()

    app_section = _as_mapping(secrets_dict.get("app"))
    sheet_section = _as_mapping(secrets_dict.get("google_sheet"))
    worksheets_section = _as_mapping(secrets_dict.get("worksheets"))
    local_csv_section = _as_mapping(secrets_dict.get("local_csv"))
    auth_section = _as_mapping(secrets_dict.get("auth"))
    service_account_info = _as_mapping(secrets_dict.get("gcp_service_account"))

    local_csv_dir = _resolve_path(
        resolved_base_dir,
        _string_or_none(local_csv_section.get("base_dir")) or "data/local_dev",
    )

    return AppSettings(
        app_name=_string_or_none(app_section.get("app_name")) or "GlipMath",
        environment=_string_or_none(app_section.get("environment")) or "local",
        timezone=_string_or_none(app_section.get("timezone")) or "America/Sao_Paulo",
        storage_backend=_string_or_none(app_section.get("storage_backend")) or "google_sheets",
        app_version=_string_or_none(app_section.get("app_version")) or "0.1.0",
        google_sheet=GoogleSheetSettings(
            spreadsheet_id=_string_or_none(sheet_section.get("spreadsheet_id")),
            spreadsheet_url=_string_or_none(sheet_section.get("spreadsheet_url")),
            retry_attempts=_int_or_default(sheet_section.get("retry_attempts"), 3),
        ),
        worksheets=WorksheetNames(
            question_bank=_string_or_none(worksheets_section.get("question_bank")) or "question_bank",
            whitelist=_string_or_none(worksheets_section.get("whitelist")) or "whitelist",
            answers=_string_or_none(worksheets_section.get("answers")) or "answers",
        ),
        local_csv_base_dir=local_csv_dir,
        auth=AuthSettings(
            redirect_uri=_string_or_none(auth_section.get("redirect_uri")),
            cookie_secret=_string_or_none(auth_section.get("cookie_secret")),
            client_id=_string_or_none(auth_section.get("client_id")),
            client_secret=_string_or_none(auth_section.get("client_secret")),
            server_metadata_url=_string_or_none(auth_section.get("server_metadata_url")),
        ),
        service_account_info=service_account_info or None,
    )


def _load_streamlit_secrets() -> dict[str, Any]:
    """Attempt to load Streamlit secrets, returning an empty mapping on failure."""

    try:
        import streamlit as st

        return _to_plain_dict(st.secrets)
    except Exception:
        return {}


def _to_plain_dict(value: Any) -> Any:
    """Convert Streamlit's secrets objects into plain Python types."""

    if isinstance(value, Mapping):
        return {str(key): _to_plain_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_dict(item) for item in value]
    return value


def _as_mapping(value: Any) -> dict[str, Any]:
    """Return a plain mapping for nested configuration sections."""

    if isinstance(value, Mapping):
        return {str(key): _to_plain_dict(item) for key, item in value.items()}
    return {}


def _string_or_none(value: Any) -> str | None:
    """Return a stripped string or None."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_default(value: Any, default: int) -> int:
    """Parse an integer setting or return a default."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_path(base_dir: Path, configured_path: str) -> Path:
    """Resolve a possibly relative path against the repository root."""

    path = Path(configured_path)
    return path if path.is_absolute() else (base_dir / path).resolve()
