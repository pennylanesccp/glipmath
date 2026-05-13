from __future__ import annotations

import pandas as pd
from google.cloud import bigquery

from modules.storage.bigquery_client import BigQueryClient


class UserAccessRepository:
    """Read access-scope rows that authorize authenticated users."""

    def __init__(self, bigquery_client: BigQueryClient, table_id: str) -> None:
        self._bigquery_client = bigquery_client
        self._table_id = table_id

    def load_active_user_frame(self, user_email: str) -> pd.DataFrame:
        """Load the active access rows for one normalized email."""

        query = f"""
            SELECT
                user_email,
                role,
                cohort_key,
                is_active,
                display_name,
                created_at_utc,
                updated_at_utc
            FROM `{self._table_id}`
            WHERE LOWER(TRIM(user_email)) = @user_email
              AND is_active = TRUE
            ORDER BY updated_at_utc DESC NULLS LAST, created_at_utc DESC NULLS LAST
        """
        return self._bigquery_client.query_to_dataframe(
            query,
            parameters=[bigquery.ScalarQueryParameter("user_email", "STRING", user_email)],
        )

    def load_active_students_frame(self, cohort_key: str) -> pd.DataFrame:
        """Load active student-access rows for one normalized project."""

        normalized_cohort_key = cohort_key.lower().strip()
        query = f"""
            SELECT
                user_email,
                role,
                cohort_key,
                is_active,
                display_name,
                created_at_utc,
                updated_at_utc
            FROM `{self._table_id}`
            WHERE LOWER(TRIM(cohort_key)) = @cohort_key
              AND LOWER(TRIM(role)) = 'student'
              AND is_active = TRUE
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY LOWER(TRIM(user_email)), LOWER(TRIM(cohort_key))
                ORDER BY updated_at_utc DESC NULLS LAST, created_at_utc DESC NULLS LAST
            ) = 1
            ORDER BY LOWER(TRIM(user_email))
        """
        return self._bigquery_client.query_to_dataframe(
            query,
            parameters=[bigquery.ScalarQueryParameter("cohort_key", "STRING", normalized_cohort_key)],
        )

    def append_access_row(self, row: dict[str, object]) -> None:
        """Append one canonical user-access row."""

        self._bigquery_client.insert_rows_json(
            self._table_id,
            [self._filter_row_for_table_schema(row)],
        )

    def deactivate_student_access(self, *, user_email: str, cohort_key: str) -> int | None:
        """Deactivate active student access rows for one project."""

        normalized_user_email = user_email.lower().strip()
        normalized_cohort_key = cohort_key.lower().strip()
        query = f"""
            UPDATE `{self._table_id}`
            SET
                is_active = FALSE,
                updated_at_utc = CURRENT_TIMESTAMP()
            WHERE LOWER(TRIM(user_email)) = @user_email
              AND LOWER(TRIM(cohort_key)) = @cohort_key
              AND LOWER(TRIM(role)) = 'student'
              AND is_active = TRUE
        """
        return self._bigquery_client.execute(
            query,
            parameters=[
                bigquery.ScalarQueryParameter("user_email", "STRING", normalized_user_email),
                bigquery.ScalarQueryParameter("cohort_key", "STRING", normalized_cohort_key),
            ],
        )

    def _filter_row_for_table_schema(self, row: dict[str, object]) -> dict[str, object]:
        available_columns = set(self._bigquery_client.get_table_column_names(self._table_id))
        return {
            key: value
            for key, value in row.items()
            if key in available_columns
        }
