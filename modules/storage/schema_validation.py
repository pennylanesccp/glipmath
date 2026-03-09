from __future__ import annotations

from collections.abc import Callable, Iterable

import pandas as pd


class WorksheetValidationError(ValueError):
    """Raised when a worksheet cannot be safely interpreted."""


def prepare_dataframe(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    """Return a sanitized dataframe suitable for validation."""

    if dataframe is None:
        return pd.DataFrame()
    prepared = dataframe.copy()
    prepared.columns = [str(column).strip() for column in prepared.columns]
    return prepared.fillna("")


def require_columns(
    dataframe: pd.DataFrame,
    required_columns: Iterable[str],
    worksheet_name: str,
) -> None:
    """Ensure the dataframe exposes the expected columns."""

    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        formatted = ", ".join(sorted(missing))
        raise WorksheetValidationError(
            f"Worksheet '{worksheet_name}' is missing required columns: {formatted}."
        )


def ensure_unique_integer_values(
    dataframe: pd.DataFrame,
    column_name: str,
    worksheet_name: str,
) -> None:
    """Raise if duplicate integer-like identifiers are found."""

    seen: set[int] = set()
    duplicates: set[int] = set()
    for _, row in dataframe.iterrows():
        raw_value = row.get(column_name, "")
        try:
            value = int(str(raw_value).strip())
        except (TypeError, ValueError):
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        formatted = ", ".join(str(value) for value in sorted(duplicates))
        raise WorksheetValidationError(
            f"Worksheet '{worksheet_name}' contains duplicate values in '{column_name}': {formatted}."
        )


def ensure_unique_normalized_values(
    dataframe: pd.DataFrame,
    column_name: str,
    worksheet_name: str,
    normalizer: Callable[[str | None], str],
) -> None:
    """Raise if duplicate normalized text values are found."""

    seen: set[str] = set()
    duplicates: set[str] = set()
    for _, row in dataframe.iterrows():
        value = normalizer(str(row.get(column_name, "")))
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        formatted = ", ".join(sorted(duplicates))
        raise WorksheetValidationError(
            f"Worksheet '{worksheet_name}' contains duplicate normalized values in '{column_name}': {formatted}."
        )


def worksheet_row_number(dataframe_index: int) -> int:
    """Return the original worksheet row number for a dataframe row."""

    return dataframe_index + 2
