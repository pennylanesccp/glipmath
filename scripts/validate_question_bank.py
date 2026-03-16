from __future__ import annotations

import argparse
import pandas as pd
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.services.question_service import parse_question_bank_dataframe
from scripts.bigquery_seed_utils import read_jsonl_rows


def main() -> None:
    """Validate a question bank JSONL file before loading it to BigQuery."""

    parser = argparse.ArgumentParser(description="Validate a GlipMath question bank JSONL file.")
    parser.add_argument(
        "--jsonl-path",
        type=Path,
        default=Path("sql/seeds/question_bank_template.jsonl"),
        help="Path to the JSONL file to validate.",
    )
    args = parser.parse_args()

    dataframe = pd.DataFrame(read_jsonl_rows(args.jsonl_path))
    questions, issues = parse_question_bank_dataframe(dataframe)

    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}")
        raise SystemExit(1)

    print(f"Question bank valid: {len(questions)} active question(s).")


if __name__ == "__main__":
    main()
