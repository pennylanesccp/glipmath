from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.utils.normalization import coerce_bool

SCHEMA_DIR = REPO_ROOT / "infrastructure" / "terraform" / "schemas"


def build_bigquery_client(project_id: str, location: str) -> bigquery.Client:
    """Create a BigQuery client for seed and admin scripts."""

    return bigquery.Client(project=project_id, location=location)


def read_csv_as_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load a CSV file into a dataframe with string preservation."""

    return pd.read_csv(csv_path, dtype=str, keep_default_na=False)


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    """Load a CSV file into a list of dictionaries."""

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{str(key): str(value or "") for key, value in row.items()} for row in reader]


def load_schema(schema_name: str) -> list[dict[str, Any]]:
    """Load a version-controlled BigQuery schema JSON file."""

    schema_path = SCHEMA_DIR / schema_name
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_rows_to_bigquery(
    *,
    client: bigquery.Client,
    table_id: str,
    rows: list[dict[str, Any]],
    schema_name: str,
    write_disposition: str = bigquery.WriteDisposition.WRITE_TRUNCATE,
) -> None:
    """Load typed JSON rows into BigQuery."""

    schema_payload = load_schema(schema_name)
    job_config = bigquery.LoadJobConfig(
        schema=[_schema_field_from_dict(field) for field in schema_payload],
        write_disposition=write_disposition,
    )
    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()


def coerce_rows_by_schema(
    rows: list[dict[str, str]],
    *,
    schema_name: str,
) -> list[dict[str, Any]]:
    """Coerce CSV string values into types expected by the schema."""

    schema_payload = load_schema(schema_name)
    return [_coerce_row(row, schema_payload) for row in rows]


def _coerce_row(row: dict[str, str], schema_payload: list[dict[str, Any]]) -> dict[str, Any]:
    typed_row: dict[str, Any] = {}
    for field in schema_payload:
        name = str(field["name"])
        field_type = str(field["type"]).upper()
        mode = str(field.get("mode", "NULLABLE")).upper()
        raw_value = str(row.get(name, "") or "").strip()

        if raw_value == "":
            if mode == "REQUIRED":
                raise ValueError(f"Field '{name}' is required.")
            typed_row[name] = None
            continue

        if field_type == "STRING":
            typed_row[name] = raw_value
        elif field_type == "INT64":
            typed_row[name] = int(raw_value)
        elif field_type == "FLOAT64":
            typed_row[name] = float(raw_value)
        elif field_type == "BOOL":
            typed_row[name] = coerce_bool(raw_value, default=False)
        elif field_type in {"TIMESTAMP", "DATETIME"}:
            typed_row[name] = raw_value
        else:
            raise ValueError(f"Unsupported field type '{field_type}' for field '{name}'.")
    return typed_row


def _schema_field_from_dict(field: dict[str, Any]) -> bigquery.SchemaField:
    nested_fields = [_schema_field_from_dict(item) for item in field.get("fields", [])]
    return bigquery.SchemaField(
        name=str(field["name"]),
        field_type=str(field["type"]),
        mode=str(field.get("mode", "NULLABLE")),
        description=field.get("description"),
        fields=nested_fields,
    )
