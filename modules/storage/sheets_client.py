from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from typing import Any, Mapping

import pandas as pd

from modules.config.settings import AppSettings


class StorageError(RuntimeError):
    """Raised when the configured storage backend cannot fulfill a request."""


class SheetsClient(ABC):
    """Abstract interface for worksheet storage backends."""

    @abstractmethod
    def read_worksheet(self, worksheet_name: str) -> pd.DataFrame:
        """Load a worksheet into a dataframe."""

    @abstractmethod
    def append_row(self, worksheet_name: str, row: Mapping[str, object]) -> None:
        """Append a single row to a worksheet."""


class GoogleSheetsClient(SheetsClient):
    """Google Sheets backend backed by a service account."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._client = None
        self._spreadsheet = None

    def read_worksheet(self, worksheet_name: str) -> pd.DataFrame:
        """Read worksheet values while preserving strings as entered."""

        worksheet = self._get_worksheet(worksheet_name)
        values = self._with_retry(worksheet.get_all_values)
        if not values:
            return pd.DataFrame()
        headers = values[0]
        rows = values[1:]
        return pd.DataFrame(rows, columns=headers).fillna("")

    def append_row(self, worksheet_name: str, row: Mapping[str, object]) -> None:
        """Append a row using the worksheet header order."""

        worksheet = self._get_worksheet(worksheet_name)
        headers = self._with_retry(lambda: worksheet.row_values(1))
        if not headers:
            raise StorageError(
                f"Worksheet '{worksheet_name}' must contain a header row before appends can succeed."
            )
        values = [row.get(column, "") for column in headers]
        self._with_retry(
            lambda: worksheet.append_row(values, value_input_option="USER_ENTERED")
        )

    def _get_worksheet(self, worksheet_name: str) -> Any:
        return self._with_retry(lambda: self._get_spreadsheet().worksheet(worksheet_name))

    def _get_spreadsheet(self) -> Any:
        if self._spreadsheet is None:
            client = self._get_client()
            if self._settings.google_sheet.spreadsheet_id:
                self._spreadsheet = self._with_retry(
                    lambda: client.open_by_key(self._settings.google_sheet.spreadsheet_id)
                )
            elif self._settings.google_sheet.spreadsheet_url:
                self._spreadsheet = self._with_retry(
                    lambda: client.open_by_url(self._settings.google_sheet.spreadsheet_url)
                )
            else:
                raise StorageError(
                    "Google Sheets backend requires either spreadsheet_id or spreadsheet_url."
                )
        return self._spreadsheet

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._settings.service_account_info:
                raise StorageError(
                    "Google Sheets backend requires a [gcp_service_account] section in Streamlit secrets."
                )

            try:
                import gspread
                from google.oauth2.service_account import Credentials
            except ImportError as exc:
                raise StorageError(
                    "Missing Google Sheets dependencies. Install requirements.txt first."
                ) from exc

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            credentials = Credentials.from_service_account_info(
                self._settings.service_account_info,
                scopes=scopes,
            )
            self._client = gspread.authorize(credentials)
        return self._client

    def _with_retry(self, operation: Any) -> Any:
        attempts = max(self._settings.google_sheet.retry_attempts, 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                if attempt == attempts:
                    break
                sleep(0.5 * attempt)
        raise StorageError("Google Sheets request failed after retries.") from last_error


class CsvSheetsClient(SheetsClient):
    """CSV-backed development storage."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def read_worksheet(self, worksheet_name: str) -> pd.DataFrame:
        """Load a CSV file that mirrors a worksheet."""

        path = self._worksheet_path(worksheet_name)
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    def append_row(self, worksheet_name: str, row: Mapping[str, object]) -> None:
        """Append a row to a CSV file."""

        path = self._worksheet_path(worksheet_name)
        existing = self.read_worksheet(worksheet_name)
        columns = list(existing.columns)
        for key in row.keys():
            if key not in columns:
                columns.append(key)

        row_frame = pd.DataFrame(
            [{column: row.get(column, "") for column in columns}],
            columns=columns,
        )
        if existing.empty and not list(existing.columns):
            combined = row_frame
        else:
            expanded_existing = existing.reindex(columns=columns, fill_value="")
            combined = pd.concat([expanded_existing, row_frame], ignore_index=True)
        combined.to_csv(path, index=False)

    def _worksheet_path(self, worksheet_name: str) -> Path:
        return self._base_dir / f"{worksheet_name}.csv"


def build_sheets_client(settings: AppSettings) -> SheetsClient:
    """Build the configured storage backend."""

    backend = settings.storage_backend.strip().lower()
    if backend == "csv":
        return CsvSheetsClient(settings.local_csv_base_dir)
    if backend == "google_sheets":
        return GoogleSheetsClient(settings)
    raise StorageError(f"Unsupported storage backend: {settings.storage_backend}.")
