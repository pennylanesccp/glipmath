from __future__ import annotations

import pandas as pd

from modules.domain.models import User, UserAccessEntry
from modules.storage.schema_validation import prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.datetime_utils import parse_timestamp
from modules.utils.normalization import clean_optional_text, coerce_bool, normalize_email

USER_ACCESS_RESOURCE_NAME = "user_access"
USER_ACCESS_REQUIRED_COLUMNS = [
    "user_email",
    "role",
    "cohort_key",
    "is_active",
]


def build_user(
    email: str | None,
    *,
    fallback_name: str | None = None,
    role: str,
    cohort_key: str,
) -> User | None:
    """Build a normalized app user from the authenticated identity."""

    normalized_email = normalize_email(email)
    if not normalized_email:
        return None

    normalized_role = _normalize_role(role)
    normalized_cohort_key = _normalize_cohort_key(cohort_key)
    if normalized_role == "teacher" and normalized_cohort_key != "all":
        raise ValueError("teacher access rows must use cohort_key 'all'.")
    if normalized_role == "student" and normalized_cohort_key == "all":
        raise ValueError("student access rows must use one specific cohort_key.")

    return User(
        email=normalized_email,
        name=clean_optional_text(fallback_name),
        role=normalized_role,
        cohort_key=normalized_cohort_key,
    )


def build_user_from_access_entry(
    access_entry: UserAccessEntry,
    *,
    fallback_name: str | None = None,
) -> User:
    """Build the current app user from one active access-control row."""

    user = build_user(
        access_entry.user_email,
        fallback_name=access_entry.display_name or fallback_name,
        role=access_entry.role,
        cohort_key=access_entry.cohort_key,
    )
    if user is None:
        raise ValueError("user_access row produced a blank normalized email.")
    return user


def parse_user_access_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[UserAccessEntry], list[str]]:
    """Parse and validate BigQuery-backed user access rows."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, USER_ACCESS_REQUIRED_COLUMNS, USER_ACCESS_RESOURCE_NAME)

    entries: list[UserAccessEntry] = []
    issues: list[str] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        try:
            user_email = normalize_email(row.get("user_email"))
            if not user_email:
                raise ValueError("user_email cannot be blank.")

            role = _normalize_role(row.get("role"))
            cohort_key = _normalize_cohort_key(row.get("cohort_key"))
            is_active = coerce_bool(row.get("is_active"), default=False)
            if role == "teacher" and cohort_key != "all":
                raise ValueError("teacher rows must use cohort_key 'all'.")
            if role == "student" and cohort_key == "all":
                raise ValueError("student rows must use one specific cohort_key.")

            entries.append(
                UserAccessEntry(
                    user_email=user_email,
                    role=role,
                    cohort_key=cohort_key,
                    is_active=is_active,
                    display_name=clean_optional_text(row.get("display_name")),
                    created_at_utc=parse_timestamp(row.get("created_at_utc")),
                    updated_at_utc=parse_timestamp(row.get("updated_at_utc")),
                )
            )
        except ValueError as exc:
            issues.append(f"{USER_ACCESS_RESOURCE_NAME} row {row_number}: {exc}")

    return entries, issues


def resolve_question_scope_for_user(user: User) -> str | None:
    """Return the cohort filter that should be applied to question reads."""

    return None if user.is_teacher else user.cohort_key


def _normalize_role(value: object) -> str:
    role = clean_optional_text(value)
    if not role:
        raise ValueError("role cannot be blank.")
    normalized = role.lower()
    if normalized not in {"student", "teacher"}:
        raise ValueError("role must be 'student' or 'teacher'.")
    return normalized


def _normalize_cohort_key(value: object) -> str:
    cohort_key = clean_optional_text(value)
    if not cohort_key:
        raise ValueError("cohort_key cannot be blank.")
    return cohort_key.lower()
