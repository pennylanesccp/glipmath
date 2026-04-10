from app.pages.professor_page import (
    USER_ACCESS_WRITE_PERMISSION_ERROR_HINT,
    _format_add_student_error,
    _is_user_access_write_permission_error,
)
from modules.storage.bigquery_client import BigQueryError


def test_detects_user_access_write_permission_error() -> None:
    message = (
        "BigQuery insert failed: 403 POST https://bigquery.googleapis.com/... "
        "Permission bigquery.tables.updateData denied on table "
        "ide-math-app:glipmath_core.user_access"
    )

    assert _is_user_access_write_permission_error(message) is True


def test_formats_user_access_write_permission_error_with_actionable_hint() -> None:
    exc = BigQueryError(
        "BigQuery insert failed: Permission bigquery.tables.updateData denied on table "
        "ide-math-app:glipmath_core.user_access"
    )

    assert _format_add_student_error(exc) == USER_ACCESS_WRITE_PERMISSION_ERROR_HINT


def test_keeps_unrelated_add_student_errors_unchanged() -> None:
    exc = ValueError("E-mail invalido.")

    assert _format_add_student_error(exc) == "E-mail invalido."
