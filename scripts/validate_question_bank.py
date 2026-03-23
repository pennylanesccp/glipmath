from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.question_bank_import_service import (
    QuestionImportFailure,
    apply_cohort_key_override,
    format_question_import_failure,
    is_staged_question_root,
    load_question_bank_import_rows,
    load_staged_question_bank_import_rows,
)
from modules.services.question_service import find_valid_question_bank_row_indexes


def main() -> None:
    """Validate question-bank input before loading it to BigQuery."""

    parser = argparse.ArgumentParser(description="Validate GlipMath question-bank input.")
    parser.add_argument(
        "--input-path",
        type=Path,
        default=Path("data"),
        help="Path to a question CSV, canonical JSONL, a plain directory, or a staged data root.",
    )
    parser.add_argument(
        "--cohort-key",
        default=None,
        help="Optional cohort_key applied to every imported question row before validation.",
    )
    args = parser.parse_args()

    try:
        if is_staged_question_root(args.input_path):
            imported_rows, import_failures, _ = load_staged_question_bank_import_rows(args.input_path)
        else:
            imported_rows, import_failures = load_question_bank_import_rows(args.input_path)
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

    if failures:
        for failure in failures:
            print(f"[ERROR] {format_question_import_failure(failure)}")
        raise SystemExit(1)

    print(f"Question bank valid: {len(valid_indexes)} active question(s) from '{args.input_path}'.")


if __name__ == "__main__":
    main()
