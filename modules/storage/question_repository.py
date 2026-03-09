from __future__ import annotations

import pandas as pd

from modules.storage.sheets_client import SheetsClient


class QuestionRepository:
    """Read-only access to the question bank worksheet."""

    def __init__(self, sheets_client: SheetsClient, worksheet_name: str) -> None:
        self._sheets_client = sheets_client
        self._worksheet_name = worksheet_name

    def load_frame(self) -> pd.DataFrame:
        """Load the raw question bank worksheet."""

        return self._sheets_client.read_worksheet(self._worksheet_name)
