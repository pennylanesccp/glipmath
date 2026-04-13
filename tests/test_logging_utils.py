from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from modules.utils.logging_utils import _StructuredLogFormatter


def test_structured_log_formatter_uses_bracketed_prefix_and_aligned_fields() -> None:
    formatter = _StructuredLogFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    formatter.converter = time.gmtime
    record = logging.LogRecord(
        name="glipmath.modules.storage.bigquery_client",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Initialized BigQuery client | project_id=%s | location=%s | auth_mode=%s",
        args=("ide-math-app", "southamerica-east1", "streamlit_service_account"),
        exc_info=None,
    )
    record.created = datetime(2026, 4, 13, 13, 42, 50, tzinfo=timezone.utc).timestamp()
    record.msecs = 0

    formatted = formatter.format(record)

    assert formatted.startswith(
        "[2026-04-13 13:42:50][INFO][glipmath.modules.storage.bigquery_client] "
        "Initialized BigQuery client"
    )
    assert "\n  project_id: ide-math-app" in formatted
    assert "\n  location  : southamerica-east1" in formatted
    assert "\n  auth_mode : streamlit_service_account" in formatted


def test_structured_log_formatter_pretty_prints_sql_and_json_like_fields() -> None:
    formatter = _StructuredLogFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    formatter.converter = time.gmtime
    record = logging.LogRecord(
        name="glipmath.modules.storage.bigquery_client",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=10,
        msg="Executing BigQuery query | location=%s | parameters=%s | sql=%s",
        args=(
            "southamerica-east1",
            [
                {
                    "name": "user_email",
                    "parameterType": {"type": "STRING"},
                    "parameterValue": {"value": "felipeproenca97@gmail.com"},
                }
            ],
            """
                SELECT
                    user_email,
                    role
                FROM `ide-math-app.glipmath_core.user_access`
                WHERE LOWER(TRIM(user_email)) = @user_email
            """,
        ),
        exc_info=None,
    )
    record.created = datetime(2026, 4, 13, 13, 42, 50, tzinfo=timezone.utc).timestamp()
    record.msecs = 0

    formatted = formatter.format(record)

    assert formatted.startswith(
        "[2026-04-13 13:42:50][DEBUG][glipmath.modules.storage.bigquery_client] "
        "Executing BigQuery query"
    )
    assert "\n  location  : southamerica-east1" in formatted
    assert "\n  parameters:" in formatted
    assert '"name": "user_email"' in formatted
    assert "\n  sql       :" in formatted
    assert "\n    SELECT" in formatted
    assert "\n        user_email," in formatted
    assert "\n    FROM `ide-math-app.glipmath_core.user_access`" in formatted
