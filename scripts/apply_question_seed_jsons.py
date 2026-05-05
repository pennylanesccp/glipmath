from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.utils.normalization import normalize_taxonomy_value
from scripts.bigquery_seed_utils import build_bigquery_client, load_rows_to_bigquery
from scripts.question_seed_ids import resolve_seed_question_id
from scripts.render_question_seed_sql import load_seed_payload

DEFAULT_INPUT_DIR = Path("local/bq_seeds/source")


@dataclass(frozen=True, slots=True)
class SeedBatch:
    source_path: Path
    table_id: str
    delete_scope: dict[str, Any]
    rows: list[dict[str, Any]]


def materialize_seed_payload(
    payload: Mapping[str, Any],
    *,
    source_path: Path,
    table_id_override: str | None = None,
    generated_at: datetime | None = None,
) -> SeedBatch:
    """Merge defaults into one seed payload and return BigQuery-ready rows."""

    table_id = _require_string(table_id_override or payload.get("table_id"), "table_id")
    delete_scope = dict(_require_mapping(payload.get("delete") or {}, "delete"))
    defaults = dict(_require_mapping(payload.get("defaults") or {}, "defaults"))
    questions_raw = payload.get("questions")
    if not isinstance(questions_raw, list) or not questions_raw:
        raise ValueError("questions must be a non-empty array.")

    generated_at_value = generated_at or datetime.now(timezone.utc)
    timestamp_value = generated_at_value.isoformat()
    rows: list[dict[str, Any]] = []
    seen_question_ids: set[int] = set()
    for index, question_raw in enumerate(questions_raw):
        question = _require_mapping(question_raw, f"questions[{index}]")
        merged_question = dict(defaults)
        merged_question.update(question)
        id_question = resolve_seed_question_id(
            merged_question.get("id_question"),
            field_name=f"questions[{index}].id_question",
            seen_question_ids=seen_question_ids,
        )

        row = {
            "id_question": id_question,
            "statement": _require_string(merged_question.get("statement"), f"questions[{index}].statement"),
            "correct_answer": _normalize_answer(
                merged_question.get("correct_answer"),
                field_name=f"questions[{index}].correct_answer",
            ),
            "wrong_answers": _normalize_wrong_answers(
                merged_question.get("wrong_answers"),
                field_name=f"questions[{index}].wrong_answers",
            ),
            "subject": _optional_taxonomy_string(merged_question.get("subject")),
            "topic": _optional_taxonomy_string(merged_question.get("topic")),
            "difficulty": _optional_string(merged_question.get("difficulty")),
            "source": _optional_string(merged_question.get("source")),
            "cohort_key": _optional_string(merged_question.get("cohort_key")),
            "is_active": _require_bool(merged_question.get("is_active"), f"questions[{index}].is_active"),
            "created_at_utc": merged_question.get("created_at_utc") or timestamp_value,
            "updated_at_utc": merged_question.get("updated_at_utc") or timestamp_value,
        }
        rows.append(row)

    return SeedBatch(
        source_path=source_path,
        table_id=table_id,
        delete_scope=delete_scope,
        rows=rows,
    )


def load_seed_batches(
    input_dir: Path,
    *,
    table_id_override: str | None = None,
) -> list[SeedBatch]:
    """Load and validate all JSON seed batches under one directory."""

    if not input_dir.exists():
        raise ValueError(f"Seed JSON directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise ValueError(f"Seed JSON input must be a directory: {input_dir}")

    input_paths = sorted(path for path in input_dir.rglob("*.json") if path.is_file())
    if not input_paths:
        raise ValueError(f"No seed JSON files were found under: {input_dir}")

    batches = [
        materialize_seed_payload(
            load_seed_payload(input_path),
            source_path=input_path,
            table_id_override=table_id_override,
        )
        for input_path in input_paths
    ]
    _validate_cross_batch_duplicates(batches)
    return batches


def apply_seed_batches(
    *,
    client: bigquery.Client,
    batches: list[SeedBatch],
) -> None:
    """Delete scoped rows and append one batch at a time."""

    for batch in batches:
        if batch.delete_scope:
            _delete_batch_rows(client=client, table_id=batch.table_id, delete_scope=batch.delete_scope)
        load_rows_to_bigquery(
            client=client,
            table_id=batch.table_id,
            rows=batch.rows,
            schema_name="question_bank.json",
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )


def _delete_batch_rows(
    *,
    client: bigquery.Client,
    table_id: str,
    delete_scope: Mapping[str, Any],
) -> None:
    if not delete_scope:
        return

    where_clauses = []
    query_parameters: list[bigquery.ScalarQueryParameter] = []
    for index, (column_name, value) in enumerate(delete_scope.items(), start=1):
        parameter_name = f"scope_{index}"
        where_clauses.append(f"{column_name} = @{parameter_name}")
        query_parameters.append(
            bigquery.ScalarQueryParameter(
                parameter_name,
                _bigquery_scalar_type(value),
                value,
            )
        )

    sql = f"DELETE FROM `{table_id}` WHERE " + " AND ".join(where_clauses)
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    client.query(sql, job_config=job_config).result()


def _validate_cross_batch_duplicates(batches: list[SeedBatch]) -> None:
    seen: dict[tuple[str, int], Path] = {}
    for batch in batches:
        for row in batch.rows:
            key = (batch.table_id, int(row["id_question"]))
            previous = seen.get(key)
            if previous is not None:
                raise ValueError(
                    "Duplicate id_question across seed batches: "
                    f"{row['id_question']} in {previous} and {batch.source_path}"
                )
            seen[key] = batch.source_path


def _normalize_answer(value: Any, *, field_name: str) -> dict[str, Any]:
    answer = _require_mapping(value, field_name)
    return {
        "alternative_text": _require_string(answer.get("alternative_text"), f"{field_name}.alternative_text"),
        "explanation": _optional_string(answer.get("explanation")),
    }


def _normalize_wrong_answers(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty array.")
    return [
        _normalize_answer(item, field_name=f"{field_name}[{index}]")
        for index, item in enumerate(value)
    ]


def _bigquery_scalar_type(value: Any) -> str:
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    return "STRING"


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object.")
    return value


def _require_string(value: Any, field_name: str) -> str:
    text = _optional_string(value)
    if text is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_taxonomy_string(value: Any) -> str | None:
    return normalize_taxonomy_value(value)


def _require_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply local question seed JSON payloads directly to BigQuery.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing JSON payloads. Defaults to {DEFAULT_INPUT_DIR.as_posix()}.",
    )
    parser.add_argument("--project-id", default="ide-math-app")
    parser.add_argument("--location", default="southamerica-east1")
    parser.add_argument(
        "--table-id",
        help="Optional override for payload.table_id across every JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate payloads and print the batches without writing to BigQuery.",
    )
    args = parser.parse_args()

    batches = load_seed_batches(args.input_dir, table_id_override=args.table_id)
    if args.dry_run:
        for batch in batches:
            print(
                f"[DRY-RUN] {batch.source_path}: table={batch.table_id} "
                f"delete_scope={batch.delete_scope} rows={len(batch.rows)}"
            )
        return

    client = build_bigquery_client(args.project_id, args.location)
    apply_seed_batches(client=client, batches=batches)
    for batch in batches:
        print(
            f"Applied seed batch: {batch.source_path} -> {batch.table_id} "
            f"(delete_scope={batch.delete_scope}, rows={len(batch.rows)})"
        )


if __name__ == "__main__":
    main()
