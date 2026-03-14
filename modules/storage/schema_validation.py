from __future__ import annotations

from collections.abc import Callable, Iterable

import pandas as pd


class DataValidationError(ValueError):
    """Raised when a dataset extract cannot be safely interpreted."""


WorksheetValidationError = DataValidationError


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
    resource_name: str,
) -> None:
    """Ensure the dataframe exposes the expected columns."""

    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        formatted = ", ".join(sorted(missing))
        raise DataValidationError(
            f"Resource '{resource_name}' is missing required columns: {formatted}."
        )


def ensure_unique_integer_values(
    dataframe: pd.DataFrame,
    column_name: str,
    resource_name: str,
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
        raise DataValidationError(
            f"Resource '{resource_name}' contains duplicate values in '{column_name}': {formatted}."
        )


def ensure_unique_normalized_values(
    dataframe: pd.DataFrame,
    column_name: str,
    resource_name: str,
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
        raise DataValidationError(
            f"Resource '{resource_name}' contains duplicate normalized values in '{column_name}': {formatted}."
        )


def worksheet_row_number(dataframe_index: int) -> int:
    """Return a human-friendly row number for CSV-style diagnostics."""

    return dataframe_index + 2
