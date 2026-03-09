from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from modules.config.settings import load_settings
from modules.services.question_service import parse_question_bank_dataframe
from modules.storage.question_repository import QuestionRepository
from modules.storage.sheets_client import StorageError, build_sheets_client


def main() -> int:
    """Validate the question bank from a CSV path or the configured backend."""

    parser = argparse.ArgumentParser(description="Validate the GlipMath question bank.")
    parser.add_argument(
        "--csv-path",
        type=Path,
        help="Optional CSV file to validate instead of the configured storage backend.",
    )
    args = parser.parse_args()

    try:
        frame = _load_frame(args.csv_path)
        questions, issues = parse_question_bank_dataframe(frame)
    except (StorageError, ValueError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    if issues:
        print("Question bank has validation issues:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(f"Validated {len(questions)} active question(s) with no blocking issues.")
    return 0


def _load_frame(csv_path: Path | None) -> pd.DataFrame:
    if csv_path is not None:
        return pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    base_dir = Path(__file__).resolve().parents[1]
    settings = load_settings(base_dir=base_dir)
    repository = QuestionRepository(
        build_sheets_client(settings),
        settings.worksheets.question_bank,
    )
    return repository.load_frame()


if __name__ == "__main__":
    raise SystemExit(main())
