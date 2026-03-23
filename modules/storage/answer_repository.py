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
        "cohort_key",
        "app_version",
    )

    def __init__(
        self,
        bigquery_client: BigQueryClient,
        *,
        answers_table_id: str,
        user_access_table_id: str,
    ) -> None:
        self._bigquery_client = bigquery_client
        self._answers_table_id = answers_table_id
        self._user_access_table_id = user_access_table_id

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

    def load_leaderboard_frame(self, *, role: str, cohort_key: str | None = None) -> pd.DataFrame:
        """Load a global or cohort-scoped leaderboard directly from BigQuery."""

        parameters: list[bigquery.ScalarQueryParameter] = []
        cohort_filter = ""
        if role == "student":
            if not cohort_key:
                raise ValueError("student leaderboard queries require cohort_key.")
            parameters.append(
                bigquery.ScalarQueryParameter("cohort_key", "STRING", cohort_key.lower())
            )
            cohort_filter = """
              AND LOWER(TRIM(answers.cohort_key)) = @cohort_key
              AND access.role = 'student'
              AND access.cohort_key = @cohort_key
            """

        query = f"""
            WITH active_access AS (
                SELECT
                    LOWER(TRIM(user_email)) AS user_email,
                    LOWER(TRIM(role)) AS role,
                    LOWER(TRIM(cohort_key)) AS cohort_key,
                    COALESCE(NULLIF(TRIM(display_name), ''), LOWER(TRIM(user_email))) AS display_name
                FROM `{self._user_access_table_id}`
                WHERE is_active = TRUE
                  AND user_email IS NOT NULL
                  AND TRIM(user_email) != ''
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY LOWER(TRIM(user_email))
                    ORDER BY updated_at_utc DESC NULLS LAST, created_at_utc DESC NULLS LAST
                ) = 1
            ),
            aggregated_answers AS (
                SELECT
                    LOWER(TRIM(answers.user_email)) AS user_email,
                    COUNT(*) AS total_answers,
                    COUNTIF(answers.is_correct) AS total_correct
                FROM `{self._answers_table_id}` AS answers
                INNER JOIN active_access AS access
                    ON access.user_email = LOWER(TRIM(answers.user_email))
                WHERE answers.user_email IS NOT NULL
                  AND TRIM(answers.user_email) != ''
                  {cohort_filter}
                GROUP BY LOWER(TRIM(answers.user_email))
            )
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY aggregated_answers.total_correct DESC,
                             aggregated_answers.total_answers DESC,
                             aggregated_answers.user_email ASC
                ) AS rank,
                aggregated_answers.user_email,
                access.display_name,
                aggregated_answers.total_correct,
                aggregated_answers.total_answers
            FROM aggregated_answers
            INNER JOIN active_access AS access
                ON access.user_email = aggregated_answers.user_email
            ORDER BY rank
        """
        return self._bigquery_client.query_to_dataframe(query, parameters=parameters or None)

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
