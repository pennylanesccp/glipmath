from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modules.config.settings import load_settings
from modules.services.answer_service import parse_answers_dataframe
from modules.storage.answer_repository import AnswerRepository
from modules.storage.sheets_client import build_sheets_client


def main() -> int:
    """Print a compact answers summary from the configured backend."""

    parser = argparse.ArgumentParser(description="Inspect GlipMath answer history.")
    parser.add_argument("--top", type=int, default=10, help="Number of rows to print.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    settings = load_settings(base_dir=base_dir)
    repository = AnswerRepository(
        build_sheets_client(settings),
        settings.worksheets.answers,
    )
    frame = repository.load_frame()
    answers, issues = parse_answers_dataframe(frame)

    print(f"Loaded {len(answers)} answer record(s).")
    if issues:
        print("Ignored malformed rows:")
        for issue in issues:
            print(f"- {issue}")

    if not answers:
        return 0

    summary = pd.DataFrame(
        [
            {
                "id_answer": answer.id_answer,
                "email": answer.email,
                "id_question": answer.id_question,
                "is_correct": answer.is_correct,
                "answered_at_utc": answer.answered_at_utc.isoformat(),
            }
            for answer in answers[: args.top]
        ]
    )
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
