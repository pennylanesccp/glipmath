from __future__ import annotations

from typing import Mapping

import pandas as pd
from google.cloud import bigquery

from modules.storage.bigquery_client import BigQueryClient


class AnswerRepository:
    """Read and append access to answers and leaderboard analytics."""

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

    def load_user_frame(self, id_user: int) -> pd.DataFrame:
        """Load answer history for a single user."""

        query = f"""
            SELECT
                id_answer,
                id_user,
                email,
                id_question,
                selected_choice,
                correct_choice,
                is_correct,
                answered_at_utc,
                answered_at_local,
                time_spent_seconds,
                session_id,
                source,
                topic,
                app_version
            FROM `{self._answers_table_id}`
            WHERE id_user = @id_user
            ORDER BY answered_at_utc DESC, id_answer DESC
        """
        return self._bigquery_client.query_to_dataframe(
            query,
            parameters=[bigquery.ScalarQueryParameter("id_user", "INT64", id_user)],
        )

    def append_answer_row(self, row: Mapping[str, object]) -> None:
        """Append a single answer log row."""

        self._bigquery_client.insert_rows_json(self._answers_table_id, [row])

    def load_leaderboard_frame(self) -> pd.DataFrame:
        """Load the leaderboard view."""

        query = f"""
            SELECT
                rank,
                id_user,
                email,
                display_name,
                total_correct,
                total_answers
            FROM `{self._leaderboard_view_id}`
            ORDER BY rank
        """
        return self._bigquery_client.query_to_dataframe(query)
