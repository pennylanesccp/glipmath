from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = REPO_ROOT / ".streamlit" / "secrets.toml"


def main() -> None:
    """Create `.streamlit/secrets.toml` from environment variables when needed."""

    if TARGET_PATH.exists():
        return

    auth_values = {
        "redirect_uri": os.getenv("STREAMLIT_AUTH_REDIRECT_URI", ""),
        "cookie_secret": os.getenv("STREAMLIT_AUTH_COOKIE_SECRET", ""),
        "client_id": os.getenv("STREAMLIT_AUTH_CLIENT_ID", ""),
        "client_secret": os.getenv("STREAMLIT_AUTH_CLIENT_SECRET", ""),
        "server_metadata_url": os.getenv("STREAMLIT_AUTH_SERVER_METADATA_URL", ""),
    }
    if not any(auth_values.values()):
        return

    content = _build_toml(auth_values)
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PATH.write_text(content, encoding="utf-8")


def _build_toml(auth_values: dict[str, str]) -> str:
    sections = {
        "app": {
            "app_name": os.getenv("GLIPMATH_APP_NAME", "GlipMath"),
            "environment": os.getenv("GLIPMATH_ENVIRONMENT", "cloud"),
            "timezone": os.getenv("GLIPMATH_TIMEZONE", "America/Sao_Paulo"),
            "app_version": os.getenv("GLIPMATH_APP_VERSION", "0.1.0"),
        },
        "gcp": {
            "project_id": os.getenv(
                "GLIPMATH_GCP_PROJECT_ID",
                os.getenv("GOOGLE_CLOUD_PROJECT", "ide-math-app"),
            ),
            "region": os.getenv("GLIPMATH_REGION", "southamerica-east1"),
        },
        "bigquery": {
            "core_dataset": os.getenv("GLIPMATH_BIGQUERY_CORE_DATASET", "glipmath_core"),
            "events_dataset": os.getenv("GLIPMATH_BIGQUERY_EVENTS_DATASET", "glipmath_events"),
            "analytics_dataset": os.getenv("GLIPMATH_BIGQUERY_ANALYTICS_DATASET", "glipmath_analytics"),
            "question_bank_table": os.getenv("GLIPMATH_QUESTION_BANK_TABLE", "question_bank"),
            "whitelist_table": os.getenv("GLIPMATH_WHITELIST_TABLE", "whitelist"),
            "answers_table": os.getenv("GLIPMATH_ANSWERS_TABLE", "answers"),
            "leaderboard_view": os.getenv("GLIPMATH_LEADERBOARD_VIEW", "v_leaderboard"),
            "user_totals_view": os.getenv("GLIPMATH_USER_TOTALS_VIEW", "v_user_totals"),
            "user_daily_activity_view": os.getenv("GLIPMATH_USER_DAILY_ACTIVITY_VIEW", "v_user_daily_activity"),
        },
        "cloud_run": {
            "service_name": os.getenv("GLIPMATH_CLOUD_RUN_SERVICE", "glipmath-app"),
        },
        "auth": auth_values,
    }

    lines: list[str] = []
    for section_name, values in sections.items():
        lines.append(f"[{section_name}]")
        for key, value in values.items():
            lines.append(f'{key} = "{_escape_toml_string(value)}"')
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    main()
