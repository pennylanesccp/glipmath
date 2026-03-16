from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


class BigQueryError(RuntimeError):
    """Raised when a BigQuery operation fails."""


class BigQueryClient:
    """Small wrapper around the official BigQuery client."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        service_account_info: Mapping[str, Any] | None = None,
    ) -> None:
        credentials = None
        if service_account_info:
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    dict(service_account_info)
                )
            except Exception as exc:
                raise BigQueryError(
                    "Invalid BigQuery service-account credentials in Streamlit secrets."
                ) from exc

        self._location = location
        try:
            self._client = bigquery.Client(
                project=project_id,
                location=location,
                credentials=credentials,
            )
        except Exception as exc:
            raise BigQueryError(
                "BigQuery credentials are not configured. Add a valid [gcp_service_account] "
                "block to Streamlit secrets or configure Application Default Credentials locally."
            ) from exc

    def query_to_dataframe(
        self,
        sql: str,
        *,
        parameters: Sequence[bigquery.ScalarQueryParameter] | None = None,
    ) -> pd.DataFrame:
        """Execute a query and return the results as a dataframe."""

        job_config = bigquery.QueryJobConfig(query_parameters=list(parameters or []))
        try:
            result = self._client.query(
                sql,
                job_config=job_config,
                location=self._location,
            ).result()
        except Exception as exc:
            raise BigQueryError("BigQuery query failed.") from exc
        return pd.DataFrame([dict(row.items()) for row in result])

    def execute(
        self,
        sql: str,
        *,
        parameters: Sequence[bigquery.ScalarQueryParameter] | None = None,
    ) -> None:
        """Execute a statement that does not need a dataframe result."""

        job_config = bigquery.QueryJobConfig(query_parameters=list(parameters or []))
        try:
            self._client.query(
                sql,
                job_config=job_config,
                location=self._location,
            ).result()
        except Exception as exc:
            raise BigQueryError("BigQuery statement failed.") from exc

    def insert_rows_json(self, table_id: str, rows: Sequence[Mapping[str, Any]]) -> None:
        """Append JSON rows to a BigQuery table."""

        if not rows:
            return
        try:
            errors = self._client.insert_rows_json(table_id, list(rows))
        except Exception as exc:
            raise BigQueryError("BigQuery insert failed.") from exc

        if errors:
            raise BigQueryError(f"BigQuery insert returned errors: {errors}")
