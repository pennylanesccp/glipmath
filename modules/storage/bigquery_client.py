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
            credentials = service_account.Credentials.from_service_account_info(
                dict(service_account_info)
            )

        self._location = location
        self._client = bigquery.Client(
            project=project_id,
            location=location,
            credentials=credentials,
        )

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
