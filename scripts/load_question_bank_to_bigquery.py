from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.question_bank_import_service import (
    QuestionImportFailure,
    StagedQuestionRoots,
    apply_cohort_key_override,
    format_question_import_failure,
    load_question_bank_import_rows,
    load_staged_question_bank_import_rows,
    is_staged_question_root,
    reconcile_staged_question_files,
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
        help="Path to a question CSV, canonical JSONL, a plain directory, or a staged data root.",
    )
    parser.add_argument(
        "--failed-rows-output",
        type=Path,
        default=None,
        help=(
            "Optional CSV report path for skipped rows. Defaults to "
            "data/new/question_bank_failed_rows.csv for staged roots or "
            "trash/<input>_failed_rows.csv otherwise."
        ),
    )
    parser.add_argument(
        "--cohort-key",
        default=None,
        help="Optional cohort_key applied to every imported question row before validation/load.",
    )
    args = parser.parse_args()

    try:
        if is_staged_question_root(args.input_path):
            imported_rows, import_failures, staged_roots = load_staged_question_bank_import_rows(
                args.input_path
            )
        else:
            imported_rows, import_failures = load_question_bank_import_rows(args.input_path)
            staged_roots = None
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc

    scoped_imported_rows = apply_cohort_key_override(imported_rows, args.cohort_key)
    valid_indexes, validation_issues = find_valid_question_bank_row_indexes(
        [item.row for item in scoped_imported_rows]
    )
    validation_failures = [
        QuestionImportFailure(
            source_file=scoped_imported_rows[issue.row_index].source_file,
            source_path=scoped_imported_rows[issue.row_index].source_path,
            row_number=scoped_imported_rows[issue.row_index].row_number,
            error=issue.message,
            raw_row=scoped_imported_rows[issue.row_index].raw_row or scoped_imported_rows[issue.row_index].row,
            raw_line=scoped_imported_rows[issue.row_index].raw_line,
        )
        for issue in validation_issues
    ]
    failures = [*import_failures, *validation_failures]
    valid_imported_rows = [scoped_imported_rows[index] for index in valid_indexes]
    if failures:
        for failure in failures:
            print(f"[WARN] {format_question_import_failure(failure)}")

    rows = [item.row for item in valid_imported_rows]
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

    failed_rows_output = args.failed_rows_output or _default_failed_rows_output(
        args.input_path,
        staged_roots=staged_roots,
    )
    if staged_roots is not None:
        reconcile_staged_question_files(
            processed_root=staged_roots.processed_root,
            new_root=staged_roots.new_root,
            imported_rows=valid_imported_rows,
            failures=failures,
        )
    if failures:
        write_question_import_failures_csv(failures, failed_rows_output)
        print(f"[WARN] Wrote {len(failures)} skipped row(s) to '{failed_rows_output}'.")
    elif failed_rows_output.exists():
        failed_rows_output.unlink()

    print(f"Loaded {len(rows)} row(s) into {table_id} from '{args.input_path}'.")


def _default_failed_rows_output(
    input_path: Path,
    *,
    staged_roots: StagedQuestionRoots | None = None,
) -> Path:
    """Return the default location for the skipped-row report."""

    if staged_roots is not None:
        return staged_roots.new_root / "question_bank_failed_rows.csv"
    stem = input_path.stem if input_path.is_file() else "question_bank"
    return Path("trash") / f"{stem}_failed_rows.csv"


if __name__ == "__main__":
    main()
