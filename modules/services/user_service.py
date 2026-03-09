from __future__ import annotations

import pandas as pd

from modules.domain.models import AppUser
from modules.storage.schema_validation import (
    ensure_unique_integer_values,
    ensure_unique_normalized_values,
    prepare_dataframe,
    require_columns,
    worksheet_row_number,
)
from modules.utils.normalization import clean_optional_text, coerce_bool, normalize_email

WHITELIST_WORKSHEET_NAME = "whitelist"
WHITELIST_REQUIRED_COLUMNS = ["id_user", "email"]


def parse_whitelist_dataframe(dataframe: pd.DataFrame) -> tuple[list[AppUser], list[str]]:
    """Parse and validate whitelist rows."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, WHITELIST_REQUIRED_COLUMNS, WHITELIST_WORKSHEET_NAME)
    ensure_unique_integer_values(prepared, "id_user", WHITELIST_WORKSHEET_NAME)
    ensure_unique_normalized_values(
        prepared,
        "email",
        WHITELIST_WORKSHEET_NAME,
        normalize_email,
    )

    users: list[AppUser] = []
    issues: list[str] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        try:
            id_user = _parse_required_int(row.get("id_user"), "id_user")
            email = normalize_email(str(row.get("email", "")))
            if not email:
                raise ValueError("email cannot be blank.")
            users.append(
                AppUser(
                    id_user=id_user,
                    email=email,
                    name=clean_optional_text(row.get("name")),
                    is_active=coerce_bool(row.get("is_active"), default=True),
                )
            )
        except ValueError as exc:
            issues.append(f"{WHITELIST_WORKSHEET_NAME} row {row_number}: {exc}")

    return users, issues


def find_user_by_email(users: list[AppUser], email: str | None) -> AppUser | None:
    """Find a whitelist user using normalized email matching."""

    normalized_email = normalize_email(email)
    if not normalized_email:
        return None
    for user in users:
        if user.email == normalized_email:
            return user
    return None


def list_active_users(users: list[AppUser]) -> list[AppUser]:
    """Return active whitelist users only."""

    return [user for user in users if user.is_active]


def _parse_required_int(value: object, field_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid integer.") from exc
