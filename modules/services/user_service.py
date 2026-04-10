from __future__ import annotations

import pandas as pd

from modules.domain.models import User, UserAccessEntry
from modules.storage.schema_validation import prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.datetime_utils import parse_timestamp, to_iso_timestamp, utc_now
from modules.utils.normalization import clean_optional_text, coerce_bool, normalize_email

USER_ACCESS_RESOURCE_NAME = "user_access"
USER_ACCESS_REQUIRED_COLUMNS = [
    "user_email",
    "role",
    "cohort_key",
    "is_active",
]
ROLE_PRIORITY = {
    "student": 1,
    "teacher": 2,
    "admin": 3,
}


def build_user(
    email: str | None,
    *,
    fallback_name: str | None = None,
    role: str,
    cohort_key: str,
    accessible_cohort_keys: tuple[str, ...] | list[str] | None = None,
) -> User | None:
    """Build a normalized app user from the authenticated identity."""

    normalized_email = normalize_email(email)
    if not normalized_email:
        return None

    normalized_role = _normalize_role(role)
    normalized_cohort_key = _normalize_cohort_key(cohort_key)
    normalized_accessible_cohort_keys = _normalize_accessible_cohort_keys(accessible_cohort_keys)
    if normalized_role == "admin" and normalized_cohort_key != "all":
        raise ValueError("admin access rows must use cohort_key 'all'.")
    if normalized_role == "student" and normalized_cohort_key == "all":
        raise ValueError("student access rows must use one specific cohort_key.")
    if normalized_role == "student" and any(
        cohort_key == "all" for cohort_key in normalized_accessible_cohort_keys
    ):
        raise ValueError("student access rows cannot include cohort_key 'all'.")
    if normalized_cohort_key != "all" and not normalized_accessible_cohort_keys:
        normalized_accessible_cohort_keys = (normalized_cohort_key,)

    return User(
        email=normalized_email,
        name=clean_optional_text(fallback_name),
        role=normalized_role,
        cohort_key=normalized_cohort_key,
        accessible_cohort_keys=normalized_accessible_cohort_keys,
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


def build_user_from_access_entries(
    access_entries: list[UserAccessEntry],
    *,
    fallback_name: str | None = None,
) -> User:
    """Build the current app user from multiple active access-control rows."""

    active_entries = [entry for entry in access_entries if entry.is_active]
    if not active_entries:
        raise ValueError("user_access must contain at least one active row.")

    normalized_email = normalize_email(active_entries[0].user_email)
    if not normalized_email:
        raise ValueError("user_access row produced a blank normalized email.")

    highest_role = max(
        (_normalize_role(entry.role) for entry in active_entries),
        key=lambda role: ROLE_PRIORITY[role],
    )
    relevant_entries = [
        entry
        for entry in active_entries
        if _normalize_role(entry.role) == highest_role
    ]
    has_global_project_access = highest_role == "admin" or any(
        _normalize_cohort_key(entry.cohort_key) == "all" for entry in relevant_entries
    )
    accessible_cohort_keys = (
        ()
        if has_global_project_access
        else tuple(
            sorted(
                {
                    _normalize_cohort_key(entry.cohort_key)
                    for entry in relevant_entries
                    if _normalize_cohort_key(entry.cohort_key) != "all"
                }
            )
        )
    )
    cohort_key = "all" if has_global_project_access else accessible_cohort_keys[0]

    display_name = next(
        (
            clean_optional_text(entry.display_name)
            for entry in relevant_entries
            if clean_optional_text(entry.display_name)
        ),
        clean_optional_text(fallback_name),
    )

    user = build_user(
        normalized_email,
        fallback_name=display_name,
        role=highest_role,
        cohort_key=cohort_key,
        accessible_cohort_keys=accessible_cohort_keys,
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
            if role == "admin" and cohort_key != "all":
                raise ValueError("admin rows must use cohort_key 'all'.")
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

    return resolve_effective_project_for_user(user)


def resolve_effective_project_for_user(
    user: User,
    selected_project: str | None = None,
) -> str | None:
    """Return the effective project/cohort scope for the current user."""

    normalized_selected_project = _normalize_optional_cohort_key(selected_project)
    if user.has_global_project_access:
        return normalized_selected_project
    if normalized_selected_project in user.project_keys:
        return normalized_selected_project
    if user.project_keys:
        return user.project_keys[0]
    return None


def resolve_available_project_options(
    user: User,
    active_project_options: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Return the selectable project options for the current authenticated user."""

    normalized_active_projects = sorted(
        {
            normalized_project
            for project in (active_project_options or [])
            for normalized_project in [_normalize_optional_cohort_key(project)]
            if normalized_project
        }
    )
    if user.has_global_project_access:
        return normalized_active_projects

    explicit_projects = sorted({project for project in user.project_keys if project})
    if explicit_projects:
        return explicit_projects
    return normalized_active_projects


def build_student_access_row(
    email: str | None,
    *,
    cohort_key: str,
    display_name: str | None = None,
) -> dict[str, object]:
    """Build one canonical active student-access row for BigQuery inserts."""

    normalized_email = normalize_email(email)
    if not normalized_email:
        raise ValueError("Informe um e-mail válido.")

    normalized_cohort_key = _normalize_cohort_key(cohort_key)
    if normalized_cohort_key == "all":
        raise ValueError("O aluno precisa ser vinculado a um projeto específico.")

    created_at = utc_now()
    return {
        "user_email": normalized_email,
        "role": "student",
        "cohort_key": normalized_cohort_key,
        "is_active": True,
        "display_name": clean_optional_text(display_name),
        "created_at_utc": to_iso_timestamp(created_at),
        "updated_at_utc": to_iso_timestamp(created_at),
    }


def has_active_project_access(
    access_entries: list[UserAccessEntry] | tuple[UserAccessEntry, ...],
    *,
    cohort_key: str,
) -> bool:
    """Return whether the email already has active access to the target project."""

    normalized_cohort_key = _normalize_cohort_key(cohort_key)
    return any(
        entry.is_active
        and _normalize_cohort_key(entry.cohort_key) in {"all", normalized_cohort_key}
        for entry in access_entries
    )


def _normalize_role(value: object) -> str:
    role = clean_optional_text(value)
    if not role:
        raise ValueError("role cannot be blank.")
    normalized = role.lower()
    if normalized not in {"student", "teacher", "admin"}:
        raise ValueError("role must be 'student', 'teacher', or 'admin'.")
    return normalized


def _normalize_cohort_key(value: object) -> str:
    cohort_key = clean_optional_text(value)
    if not cohort_key:
        raise ValueError("cohort_key cannot be blank.")
    return cohort_key.lower()


def _normalize_optional_cohort_key(value: object) -> str | None:
    cohort_key = clean_optional_text(value)
    if not cohort_key:
        return None
    return cohort_key.lower()


def _normalize_accessible_cohort_keys(
    values: tuple[str, ...] | list[str] | None,
) -> tuple[str, ...]:
    if not values:
        return ()
    normalized_values = {
        normalized_value
        for value in values
        for normalized_value in [_normalize_optional_cohort_key(value)]
        if normalized_value
    }
    return tuple(sorted(normalized_values))
