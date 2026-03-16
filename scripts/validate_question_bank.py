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


def main() -> None:
    """Validate question-bank input before loading it to BigQuery."""

    parser = argparse.ArgumentParser(description="Validate GlipMath question-bank input.")
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
    questions, issues = parse_question_bank_dataframe(dataframe)

    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}")
        raise SystemExit(1)

    print(f"Question bank valid: {len(questions)} active question(s) from '{args.input_path}'.")


if __name__ == "__main__":
    main()
