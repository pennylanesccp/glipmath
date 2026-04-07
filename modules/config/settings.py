from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse, urlunparse


LOCAL_URL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(frozen=True, slots=True)
class AuthRedirectRuntimeStatus:
    """Runtime validation result for the configured OAuth redirect URI."""

    current_redirect_uri: str | None
    expected_redirect_uri: str | None
    issue_code: str | None

    @property
    def is_valid(self) -> bool:
        """Return whether the configured redirect URI is safe for the current runtime URL."""

        return self.issue_code is None


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

    @property
    def is_local_redirect_uri(self) -> bool:
        """Return whether the configured redirect URI points to a local host."""

        return _is_local_url(self.redirect_uri)

    def expected_redirect_uri(self, app_url: str | None) -> str | None:
        """Build the callback URL that matches the current app origin."""

        parsed_app_url = _parsed_url_or_none(app_url)
        if parsed_app_url is None:
            return None

        return urlunparse(
            (
                parsed_app_url.scheme.lower(),
                parsed_app_url.netloc.lower(),
                "/oauth2callback",
                "",
                "",
                "",
            )
        )

    def runtime_redirect_status(self, app_url: str | None) -> AuthRedirectRuntimeStatus:
        """Validate the configured redirect URI against the current app URL when available."""

        expected_redirect_uri = self.expected_redirect_uri(app_url)
        if not self.is_configured or expected_redirect_uri is None or _is_local_url(app_url):
            return AuthRedirectRuntimeStatus(
                current_redirect_uri=self.redirect_uri,
                expected_redirect_uri=expected_redirect_uri,
                issue_code=None,
            )

        if self.is_local_redirect_uri:
            return AuthRedirectRuntimeStatus(
                current_redirect_uri=self.redirect_uri,
                expected_redirect_uri=expected_redirect_uri,
                issue_code="localhost_redirect",
            )

        if not _urls_match(self.redirect_uri, expected_redirect_uri):
            return AuthRedirectRuntimeStatus(
                current_redirect_uri=self.redirect_uri,
                expected_redirect_uri=expected_redirect_uri,
                issue_code="app_url_mismatch",
            )

        return AuthRedirectRuntimeStatus(
            current_redirect_uri=self.redirect_uri,
            expected_redirect_uri=expected_redirect_uri,
            issue_code=None,
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
    user_access_table: str
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

    def user_access_table_id(self, project_id: str) -> str:
        """Return the fully qualified user-access table identifier."""

        return f"{project_id}.{self.core_dataset}.{self.user_access_table}"

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

    resolved_base_dir = (base_dir or Path.cwd()).resolve()
    public_config_dict = _load_toml_file(resolved_base_dir / "glipmath.toml")
    secrets_dict = _to_plain_dict(secrets if secrets is not None else _load_streamlit_secrets())

    app_section = _merge_sections(public_config_dict.get("app"), secrets_dict.get("app"))
    gcp_section = _merge_sections(public_config_dict.get("gcp"), secrets_dict.get("gcp"))
    bigquery_section = _merge_sections(
        public_config_dict.get("bigquery"),
        secrets_dict.get("bigquery"),
    )
    auth_section = _as_mapping(secrets_dict.get("auth"))
    ai_section = _merge_sections(public_config_dict.get("ai"), secrets_dict.get("ai"))
    service_account_section = _as_mapping(secrets_dict.get("gcp_service_account"))
    service_account_json = _string_or_none(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        or gcp_section.get("service_account_json")
    )
    service_account_info = _service_account_info_or_none(
        service_account_section or _json_mapping_or_none(service_account_json)
    )

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
            user_access_table=(
                _env_or_section(
                    "GLIPMATH_USER_ACCESS_TABLE",
                    bigquery_section,
                    "user_access_table",
                )
                or "user_access"
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


def _load_toml_file(path: Path) -> dict[str, Any]:
    """Load a TOML file into plain Python types, returning an empty mapping on failure."""

    if not path.is_file():
        return {}

    try:
        with path.open("rb") as handle:
            return _to_plain_dict(tomllib.load(handle))
    except (OSError, tomllib.TOMLDecodeError):
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


def _merge_sections(*sections: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Merge config sections from left to right, with later values taking precedence."""

    merged: dict[str, Any] = {}
    for section in sections:
        merged.update(_as_mapping(section))
    return merged


def _string_or_none(value: Any) -> str | None:
    """Return a stripped string or None."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _service_account_info_or_none(
    value: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a usable service-account mapping or None for placeholders."""

    mapping = _as_mapping(value)
    if not mapping:
        return None

    required_values = [
        _string_or_none(mapping.get("client_email")),
        _string_or_none(mapping.get("private_key")),
        _string_or_none(mapping.get("private_key_id")),
    ]
    if not all(required_values):
        return None

    if any(_looks_like_placeholder(item) for item in required_values):
        return None

    private_key = required_values[1]
    if private_key is None or "BEGIN PRIVATE KEY" not in private_key:
        return None

    return mapping


def _looks_like_placeholder(value: str) -> bool:
    return "REPLACE_WITH_" in value or "YOUR_" in value


def _parsed_url_or_none(value: str | None):
    text = _string_or_none(value)
    if not text:
        return None

    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return None
    return parsed


def _is_local_url(value: str | None) -> bool:
    parsed = _parsed_url_or_none(value)
    if parsed is None:
        return False

    hostname = (parsed.hostname or "").strip().lower()
    return hostname in LOCAL_URL_HOSTS


def _normalize_url(value: str | None) -> str | None:
    parsed = _parsed_url_or_none(value)
    if parsed is None:
        return None

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            "",
            "",
        )
    )


def _urls_match(left: str | None, right: str | None) -> bool:
    normalized_left = _normalize_url(left)
    normalized_right = _normalize_url(right)
    return normalized_left is not None and normalized_left == normalized_right
