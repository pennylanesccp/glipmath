from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_DIR = REPO_ROOT / "infrastructure" / "terraform" / "schemas"


def build_bigquery_client(project_id: str, location: str) -> bigquery.Client:
    """Create a BigQuery client for seed and admin scripts."""

    return bigquery.Client(project=project_id, location=location)


def read_jsonl_rows(jsonl_path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of dictionaries."""

    rows: list[dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of '{jsonl_path}'."
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number} of '{jsonl_path}'."
                )
            rows.append(parsed)
    return rows


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


def _schema_field_from_dict(field: dict[str, Any]) -> bigquery.SchemaField:
    nested_fields = [_schema_field_from_dict(item) for item in field.get("fields", [])]
    return bigquery.SchemaField(
        name=str(field["name"]),
        field_type=str(field["type"]),
        mode=str(field.get("mode", "NULLABLE")),
        description=field.get("description"),
        fields=nested_fields,
    )
