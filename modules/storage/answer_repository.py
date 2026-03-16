from __future__ import annotations

from typing import Mapping

import pandas as pd
from google.cloud import bigquery

from modules.storage.bigquery_client import BigQueryClient


class AnswerRepository:
    """Read and append access to answers and leaderboard analytics."""

    _REQUIRED_ANSWER_COLUMNS = (
        "id_answer",
        "id_question",
        "user_email",
        "selected_alternative_text",
        "correct_alternative_text",
        "is_correct",
        "answered_at_utc",
        "answered_at_local",
        "time_spent_seconds",
        "session_id",
    )
    _OPTIONAL_ANSWER_COLUMNS = (
        "subject",
        "topic",
        "difficulty",
        "source",
        "app_version",
    )

    def __init__(
        self,
        bigquery_client: BigQueryClient,
        *,
        answers_table_id: str,
        leaderboard_view_id: str,
    ) -> None:
        self._bigquery_client = bigquery_client
        self._answers_table_id = answers_table_id
        self._leaderboard_view_id = leaderboard_view_id

    def load_user_frame(self, user_email: str) -> pd.DataFrame:
        """Load answer history for a single user email."""

        select_columns = ",\n                ".join(self._build_answers_select_columns())
        query = f"""
            SELECT
                {select_columns}
            FROM `{self._answers_table_id}`
            WHERE LOWER(TRIM(user_email)) = @user_email
            ORDER BY answered_at_utc DESC, id_answer DESC
        """
        return self._bigquery_client.query_to_dataframe(
            query,
            parameters=[bigquery.ScalarQueryParameter("user_email", "STRING", user_email)],
        )

    def append_answer_row(self, row: Mapping[str, object]) -> None:
        """Append a single answer log row."""

        self._bigquery_client.insert_rows_json(
            self._answers_table_id,
            [self._filter_row_for_table_schema(row)],
        )

    def load_leaderboard_frame(self) -> pd.DataFrame:
        """Load the leaderboard view."""

        query = f"""
            SELECT
                rank,
                user_email,
                display_name,
                total_correct,
                total_answers
            FROM `{self._leaderboard_view_id}`
            ORDER BY rank
        """
        return self._bigquery_client.query_to_dataframe(query)

    def _build_answers_select_columns(self) -> list[str]:
        available_columns = set(self._bigquery_client.get_table_column_names(self._answers_table_id))
        select_columns = list(self._REQUIRED_ANSWER_COLUMNS)
        for column_name in self._OPTIONAL_ANSWER_COLUMNS:
            if column_name in available_columns:
                select_columns.append(column_name)
            else:
                select_columns.append(f"CAST(NULL AS STRING) AS {column_name}")
        return select_columns

    def _filter_row_for_table_schema(self, row: Mapping[str, object]) -> dict[str, object]:
        available_columns = set(self._bigquery_client.get_table_column_names(self._answers_table_id))
        return {
            key: value
            for key, value in row.items()
            if key in available_columns
        }
