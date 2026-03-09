from __future__ import annotations

from typing import Mapping

import pandas as pd

from modules.storage.sheets_client import SheetsClient


class AnswerRepository:
    """Read and append access to the answers worksheet."""

    def __init__(self, sheets_client: SheetsClient, worksheet_name: str) -> None:
        self._sheets_client = sheets_client
        self._worksheet_name = worksheet_name

    def load_frame(self) -> pd.DataFrame:
        """Load the raw answer history worksheet."""

        return self._sheets_client.read_worksheet(self._worksheet_name)

    def append_answer_row(self, row: Mapping[str, object]) -> None:
        """Append a single answer log row."""

        self._sheets_client.append_row(self._worksheet_name, row)
