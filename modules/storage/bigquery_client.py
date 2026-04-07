from __future__ import annotations

from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from modules.utils.logging_utils import get_logger


class BigQueryError(RuntimeError):
    """Raised when a BigQuery operation fails."""


logger = get_logger(__name__)


class BigQueryClient:
    """Small wrapper around the official BigQuery client."""

    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        service_account_info: Mapping[str, Any] | None = None,
        allow_application_default_credentials: bool = True,
    ) -> None:
        self._table_columns_cache: dict[str, tuple[str, ...]] = {}
        credentials = None
        auth_mode = "application_default_credentials"
        if service_account_info:
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    dict(service_account_info)
                )
                auth_mode = "streamlit_service_account"
            except Exception as exc:
                logger.exception("Invalid service-account info supplied to BigQuery client.")
                raise BigQueryError(
                    "Invalid BigQuery service-account credentials in Streamlit secrets."
                ) from exc
        elif not allow_application_default_credentials:
            logger.error(
                "Missing explicit BigQuery credentials | project_id=%s | location=%s",
                project_id,
                location,
            )
            raise BigQueryError(
                "BigQuery credentials are not configured. Add a valid [gcp_service_account] "
                "block to Streamlit secrets."
            )

        self._location = location
        try:
            self._client = bigquery.Client(
                project=project_id,
                location=location,
                credentials=credentials,
            )
        except Exception as exc:
            logger.exception(
                "Failed to initialize BigQuery client | project_id=%s | location=%s | auth_mode=%s",
                project_id,
                location,
                auth_mode,
            )
            raise BigQueryError(
                "BigQuery credentials are not configured. Add a valid [gcp_service_account] "
                "block to Streamlit secrets or configure Application Default Credentials locally."
            ) from exc
        logger.info(
            "Initialized BigQuery client | project_id=%s | location=%s | auth_mode=%s",
            project_id,
            location,
            auth_mode,
        )

    def get_table_column_names(self, table_id: str) -> tuple[str, ...]:
        """Return the top-level column names for a BigQuery table."""

        cached = self._table_columns_cache.get(table_id)
        if cached is not None:
            return cached

        try:
            logger.debug("Loading BigQuery table schema | table_id=%s", table_id)
            table = self._client.get_table(table_id)
        except Exception as exc:
            logger.exception("Failed to load BigQuery table schema | table_id=%s", table_id)
            raise BigQueryError(f"BigQuery schema lookup failed: {exc}") from exc

        column_names = tuple(field.name for field in table.schema)
        self._table_columns_cache[table_id] = column_names
        logger.debug(
            "Loaded BigQuery table schema | table_id=%s | columns=%s",
            table_id,
            list(column_names),
        )
        return column_names

    def query_to_dataframe(
        self,
        sql: str,
        *,
        parameters: Sequence[bigquery.ScalarQueryParameter] | None = None,
    ) -> pd.DataFrame:
        """Execute a query and return the results as a dataframe."""

        job_config = bigquery.QueryJobConfig(query_parameters=list(parameters or []))
        query_job = None
        query_started_at = perf_counter()
        try:
            logger.debug(
                "Executing BigQuery query | location=%s | parameters=%s | sql=%s",
                self._location,
                _format_parameters(parameters),
                _compact_sql(sql),
            )
            query_job = self._client.query(
                sql,
                job_config=job_config,
                location=self._location,
            )
            result = query_job.result()
        except Exception as exc:
            logger.exception(
                "BigQuery query failed | job_id=%s | parameters=%s | sql=%s",
                getattr(query_job, "job_id", None),
                _format_parameters(parameters),
                _compact_sql(sql),
            )
            raise BigQueryError(f"BigQuery query failed: {exc}") from exc

        materialization_started_at = perf_counter()
        column_names = [field.name for field in result.schema]
        rows = list(result)
        dataframe = pd.DataFrame.from_records(rows, columns=column_names)
        logger.debug(
            "BigQuery query succeeded | job_id=%s | rows=%s | query_elapsed_ms=%.2f | materialization_elapsed_ms=%.2f",
            getattr(query_job, "job_id", None),
            len(dataframe),
            (materialization_started_at - query_started_at) * 1000,
            (perf_counter() - materialization_started_at) * 1000,
        )
        return dataframe

    def execute(
        self,
        sql: str,
        *,
        parameters: Sequence[bigquery.ScalarQueryParameter] | None = None,
    ) -> None:
        """Execute a statement that does not need a dataframe result."""

        job_config = bigquery.QueryJobConfig(query_parameters=list(parameters or []))
        query_job = None
        try:
            logger.debug(
                "Executing BigQuery statement | location=%s | parameters=%s | sql=%s",
                self._location,
                _format_parameters(parameters),
                _compact_sql(sql),
            )
            query_job = self._client.query(
                sql,
                job_config=job_config,
                location=self._location,
            )
            query_job.result()
        except Exception as exc:
            logger.exception(
                "BigQuery statement failed | job_id=%s | parameters=%s | sql=%s",
                getattr(query_job, "job_id", None),
                _format_parameters(parameters),
                _compact_sql(sql),
            )
            raise BigQueryError(f"BigQuery statement failed: {exc}") from exc
        logger.debug(
            "BigQuery statement succeeded | job_id=%s",
            getattr(query_job, "job_id", None),
        )

    def insert_rows_json(self, table_id: str, rows: Sequence[Mapping[str, Any]]) -> None:
        """Append JSON rows to a BigQuery table."""

        if not rows:
            return
        try:
            logger.debug(
                "Inserting BigQuery rows | table_id=%s | row_count=%s",
                table_id,
                len(rows),
            )
            errors = self._client.insert_rows_json(table_id, list(rows))
        except Exception as exc:
            logger.exception(
                "BigQuery insert failed | table_id=%s | row_count=%s",
                table_id,
                len(rows),
            )
            raise BigQueryError(f"BigQuery insert failed: {exc}") from exc

        if errors:
            logger.error(
                "BigQuery insert returned errors | table_id=%s | errors=%s",
                table_id,
                errors,
            )
            raise BigQueryError(f"BigQuery insert returned errors: {errors}")
        logger.debug(
            "BigQuery insert succeeded | table_id=%s | row_count=%s",
            table_id,
            len(rows),
        )


def _compact_sql(sql: str) -> str:
    return " ".join(line.strip() for line in sql.strip().splitlines() if line.strip())


def _format_parameters(
    parameters: Sequence[bigquery.ScalarQueryParameter] | None,
) -> list[dict[str, Any]]:
    if not parameters:
        return []
    formatted: list[dict[str, Any]] = []
    for parameter in parameters:
        try:
            formatted.append(parameter.to_api_repr())
        except Exception:
            formatted.append({"value": repr(parameter)})
    return formatted
