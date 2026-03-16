from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """OIDC-related settings consumed by Streamlit auth."""

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
class GcpSettings:
    """Google Cloud runtime settings."""

    project_id: str
    location: str


@dataclass(frozen=True, slots=True)
class BigQuerySettings:
    """BigQuery dataset, table, and view names."""

    core_dataset: str
    events_dataset: str
    analytics_dataset: str
    question_bank_table: str
    answers_table: str
    leaderboard_view: str
    user_totals_view: str
    user_daily_activity_view: str

    def question_bank_table_id(self, project_id: str) -> str:
        """Return the fully qualified question bank table identifier."""

        return f"{project_id}.{self.core_dataset}.{self.question_bank_table}"

    def answers_table_id(self, project_id: str) -> str:
        """Return the fully qualified answers table identifier."""

        return f"{project_id}.{self.events_dataset}.{self.answers_table}"

    def leaderboard_view_id(self, project_id: str) -> str:
        """Return the fully qualified leaderboard view identifier."""

        return f"{project_id}.{self.analytics_dataset}.{self.leaderboard_view}"

    def user_totals_view_id(self, project_id: str) -> str:
        """Return the fully qualified user totals view identifier."""

        return f"{project_id}.{self.analytics_dataset}.{self.user_totals_view}"

    def user_daily_activity_view_id(self, project_id: str) -> str:
        """Return the fully qualified daily activity view identifier."""

        return f"{project_id}.{self.analytics_dataset}.{self.user_daily_activity_view}"


@dataclass(frozen=True, slots=True)
class GeminiSettings:
    """Gemini API settings for offline/admin enrichment workflows."""

    api_key: str | None
    model: str

    @property
    def is_configured(self) -> bool:
        """Return whether the Gemini enrichment settings are present."""

        return bool(self.api_key and self.model)


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Top-level application settings."""

    app_name: str
    environment: str
    timezone: str
    app_version: str
    repository_root: Path
    gcp: GcpSettings
    bigquery: BigQuerySettings
    auth: AuthSettings
    gemini: GeminiSettings
    service_account_info: dict[str, Any] | None


def load_settings(
    secrets: Mapping[str, Any] | None = None,
    *,
    base_dir: Path | None = None,
) -> AppSettings:
    """Load application settings from environment variables and Streamlit secrets."""

    secrets_dict = _to_plain_dict(secrets or _load_streamlit_secrets())
    resolved_base_dir = (base_dir or Path.cwd()).resolve()

    app_section = _as_mapping(secrets_dict.get("app"))
    gcp_section = _as_mapping(secrets_dict.get("gcp"))
    bigquery_section = _as_mapping(secrets_dict.get("bigquery"))
    auth_section = _as_mapping(secrets_dict.get("auth"))
    ai_section = _as_mapping(secrets_dict.get("ai"))
    service_account_section = _as_mapping(secrets_dict.get("gcp_service_account"))
    service_account_json = _string_or_none(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        or gcp_section.get("service_account_json")
    )
    service_account_info = service_account_section or _json_mapping_or_none(service_account_json)

    project_id = (
        _env_or_section("GLIPMATH_GCP_PROJECT_ID", gcp_section, "project_id")
        or _string_or_none(os.getenv("GOOGLE_CLOUD_PROJECT"))
        or _string_or_none(os.getenv("GCP_PROJECT"))
        or _string_or_none((service_account_info or {}).get("project_id"))
        or "ide-math-app"
    )

    return AppSettings(
        app_name=_env_or_section("GLIPMATH_APP_NAME", app_section, "app_name") or "GlipMath",
        environment=_env_or_section("GLIPMATH_ENVIRONMENT", app_section, "environment") or "local",
        timezone=_env_or_section("GLIPMATH_TIMEZONE", app_section, "timezone") or "America/Sao_Paulo",
        app_version=_env_or_section("GLIPMATH_APP_VERSION", app_section, "app_version") or "0.1.0",
        repository_root=resolved_base_dir,
        gcp=GcpSettings(
            project_id=project_id,
            location=_env_or_section("GLIPMATH_LOCATION", gcp_section, "location")
            or _env_or_section("GLIPMATH_REGION", gcp_section, "region")
            or "southamerica-east1",
        ),
        bigquery=BigQuerySettings(
            core_dataset=(
                _env_or_section("GLIPMATH_BIGQUERY_CORE_DATASET", bigquery_section, "core_dataset")
                or "glipmath_core"
            ),
            events_dataset=(
                _env_or_section("GLIPMATH_BIGQUERY_EVENTS_DATASET", bigquery_section, "events_dataset")
                or "glipmath_events"
            ),
            analytics_dataset=(
                _env_or_section(
                    "GLIPMATH_BIGQUERY_ANALYTICS_DATASET",
                    bigquery_section,
                    "analytics_dataset",
                )
                or "glipmath_analytics"
            ),
            question_bank_table=(
                _env_or_section(
                    "GLIPMATH_QUESTION_BANK_TABLE",
                    bigquery_section,
                    "question_bank_table",
                )
                or "question_bank"
            ),
            answers_table=(
                _env_or_section("GLIPMATH_ANSWERS_TABLE", bigquery_section, "answers_table")
                or "answers"
            ),
            leaderboard_view=(
                _env_or_section("GLIPMATH_LEADERBOARD_VIEW", bigquery_section, "leaderboard_view")
                or "v_leaderboard"
            ),
            user_totals_view=(
                _env_or_section("GLIPMATH_USER_TOTALS_VIEW", bigquery_section, "user_totals_view")
                or "v_user_totals"
            ),
            user_daily_activity_view=(
                _env_or_section(
                    "GLIPMATH_USER_DAILY_ACTIVITY_VIEW",
                    bigquery_section,
                    "user_daily_activity_view",
                )
                or "v_user_daily_activity"
            ),
        ),
        auth=AuthSettings(
            redirect_uri=_env_or_section("STREAMLIT_AUTH_REDIRECT_URI", auth_section, "redirect_uri"),
            cookie_secret=_env_or_section(
                "STREAMLIT_AUTH_COOKIE_SECRET",
                auth_section,
                "cookie_secret",
            ),
            client_id=_env_or_section("STREAMLIT_AUTH_CLIENT_ID", auth_section, "client_id"),
            client_secret=_env_or_section(
                "STREAMLIT_AUTH_CLIENT_SECRET",
                auth_section,
                "client_secret",
            ),
            server_metadata_url=_env_or_section(
                "STREAMLIT_AUTH_SERVER_METADATA_URL",
                auth_section,
                "server_metadata_url",
            ),
        ),
        gemini=GeminiSettings(
            api_key=(
                _env_or_section("GEMINI_API_KEY", ai_section, "GEMINI_API_KEY")
                or _env_or_section("GEMINI_API_KEY", ai_section, "api_key")
            ),
            model=(
                _env_or_section("GEMINI_MODEL", ai_section, "GEMINI_MODEL")
                or _env_or_section("GEMINI_MODEL", ai_section, "model")
                or "gemini-2.5-flash-lite"
            ),
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


def _env_or_section(env_name: str, section: Mapping[str, Any], key: str) -> str | None:
    """Return an environment variable value or fall back to a secrets section key."""

    return _string_or_none(os.getenv(env_name)) or _string_or_none(section.get(key))


def _json_mapping_or_none(value: str | None) -> dict[str, Any] | None:
    """Parse a JSON object string into a dictionary when present."""

    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return _as_mapping(parsed) or None


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
