from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.question_service import parse_question_bank_dataframe
from scripts.bigquery_seed_utils import (
    build_bigquery_client,
    coerce_rows_by_schema,
    load_rows_to_bigquery,
    read_csv_as_dataframe,
    read_csv_rows,
)


def main() -> None:
    """Load the curated question bank CSV into BigQuery."""

    parser = argparse.ArgumentParser(description="Load the question bank CSV into BigQuery.")
    parser.add_argument("--project-id", default="ide-math-app")
    parser.add_argument("--dataset", default="glipmath_core")
    parser.add_argument("--table", default="question_bank")
    parser.add_argument("--location", default="southamerica-east1")
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=Path("sql/seeds/question_bank_template.csv"),
    )
    args = parser.parse_args()

    dataframe = read_csv_as_dataframe(args.csv_path)
    _, issues = parse_question_bank_dataframe(dataframe)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}")
        raise SystemExit(1)

    rows = coerce_rows_by_schema(read_csv_rows(args.csv_path), schema_name="question_bank.json")
    client = build_bigquery_client(args.project_id, args.location)
    table_id = f"{args.project_id}.{args.dataset}.{args.table}"
    load_rows_to_bigquery(
        client=client,
        table_id=table_id,
        rows=rows,
        schema_name="question_bank.json",
    )
    print(f"Loaded {len(rows)} row(s) into {table_id}.")


if __name__ == "__main__":
    main()
