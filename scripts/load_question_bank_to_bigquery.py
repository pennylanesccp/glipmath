from __future__ import annotations

import argparse
import pandas as pd
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.question_bank_import_service import load_question_bank_rows
from modules.services.question_service import parse_question_bank_dataframe
from scripts.bigquery_seed_utils import (
    build_bigquery_client,
    load_rows_to_bigquery,
)


def main() -> None:
    """Load question-bank input into BigQuery.

    The load job replaces the current contents of the target table.
    """

    parser = argparse.ArgumentParser(description="Load question-bank input into BigQuery.")
    parser.add_argument("--project-id", default="ide-math-app")
    parser.add_argument("--dataset", default="glipmath_core")
    parser.add_argument("--table", default="question_bank")
    parser.add_argument("--location", default="southamerica-east1")
    parser.add_argument(
        "--input-path",
        type=Path,
        default=Path("data"),
        help="Path to a question CSV, canonical JSONL, or a directory containing them.",
    )
    args = parser.parse_args()

    try:
        rows = load_question_bank_rows(args.input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc

    dataframe = pd.DataFrame(rows)
    _, issues = parse_question_bank_dataframe(dataframe)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}")
        raise SystemExit(1)

    client = build_bigquery_client(args.project_id, args.location)
    table_id = f"{args.project_id}.{args.dataset}.{args.table}"
    load_rows_to_bigquery(
        client=client,
        table_id=table_id,
        rows=rows,
        schema_name="question_bank.json",
    )
    print(f"Loaded {len(rows)} row(s) into {table_id} from '{args.input_path}'.")


if __name__ == "__main__":
    main()
