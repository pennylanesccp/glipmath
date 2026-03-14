from __future__ import annotations

import pandas as pd

from modules.storage.bigquery_client import BigQueryClient


class QuestionRepository:
    """Read-only access to the question bank table."""

    def __init__(self, bigquery_client: BigQueryClient, table_id: str) -> None:
        self._bigquery_client = bigquery_client
        self._table_id = table_id

    def load_frame(self) -> pd.DataFrame:
        """Load active questions from BigQuery."""

        query = f"""
            SELECT
                id_question,
                source,
                statement,
                choice_a,
                choice_b,
                choice_c,
                choice_d,
                choice_e,
                correct_choice,
                is_active,
                topic,
                difficulty,
                explanation,
                created_at_utc,
                updated_at_utc
            FROM `{self._table_id}`
            WHERE is_active = TRUE
            ORDER BY id_question
        """
        return self._bigquery_client.query_to_dataframe(query)
