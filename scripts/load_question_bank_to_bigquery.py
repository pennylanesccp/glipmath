from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.question_bank_import_service import (
    QuestionImportFailure,
    format_question_import_failure,
    load_question_bank_import_rows,
    write_question_import_failures_csv,
)
from modules.services.question_service import find_valid_question_bank_row_indexes
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
    parser.add_argument(
        "--failed-rows-output",
        type=Path,
        default=None,
        help="Optional CSV report path for skipped rows. Defaults to trash/<input>_failed_rows.csv.",
    )
    args = parser.parse_args()

    try:
        imported_rows, import_failures = load_question_bank_import_rows(args.input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc

    valid_indexes, validation_issues = find_valid_question_bank_row_indexes(
        [item.row for item in imported_rows]
    )
    validation_failures = [
        QuestionImportFailure(
            source_file=imported_rows[issue.row_index].source_file,
            row_number=imported_rows[issue.row_index].row_number,
            error=issue.message,
            raw_row=imported_rows[issue.row_index].raw_row or imported_rows[issue.row_index].row,
        )
        for issue in validation_issues
    ]
    failures = [*import_failures, *validation_failures]
    if failures:
        for failure in failures:
            print(f"[WARN] {format_question_import_failure(failure)}")

        failed_rows_output = args.failed_rows_output or _default_failed_rows_output(args.input_path)
        write_question_import_failures_csv(failures, failed_rows_output)
        print(
            f"[WARN] Wrote {len(failures)} skipped row(s) to '{failed_rows_output}'."
        )

    rows = [imported_rows[index].row for index in valid_indexes]
    if not rows:
        print("[ERROR] No valid question rows remained after filtering invalid input.")
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


def _default_failed_rows_output(input_path: Path) -> Path:
    """Return the default location for the skipped-row report."""

    stem = input_path.stem if input_path.is_file() else "question_bank"
    return Path("trash") / f"{stem}_failed_rows.csv"


if __name__ == "__main__":
    main()
