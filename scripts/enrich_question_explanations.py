from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.ai.explanation_service import ExplanationService
from modules.ai.gemini_client import GeminiClient
from modules.config.settings import load_settings
from modules.services.question_service import parse_question_bank_dataframe
from modules.storage.bigquery_client import BigQueryClient
from modules.storage.question_repository import QuestionRepository


def main() -> None:
    """Enrich missing question explanations with Gemini."""

    parser = argparse.ArgumentParser(
        description="Generate missing question explanations with Gemini and write them back to BigQuery."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of questions to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate explanations without writing updates back to BigQuery.",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        print("[ERROR] --limit must be greater than zero.")
        raise SystemExit(1)

    settings = load_settings(base_dir=REPO_ROOT)
    if not settings.gemini.is_configured:
        print("[ERROR] Gemini is not configured. Add [ai].GEMINI_API_KEY and [ai].GEMINI_MODEL to secrets.")
        raise SystemExit(1)

    bigquery_client = BigQueryClient(
        project_id=settings.gcp.project_id,
        location=settings.gcp.location,
        service_account_info=settings.service_account_info,
    )
    question_repository = QuestionRepository(
        bigquery_client=bigquery_client,
        table_id=settings.bigquery.question_bank_table_id(settings.gcp.project_id),
    )
    dataframe = question_repository.load_missing_explanations_frame(limit=args.limit)
    questions, issues = parse_question_bank_dataframe(dataframe)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}")
        raise SystemExit(1)

    if not questions:
        print("No active questions with missing explanations were found.")
        return

    explanation_service = ExplanationService(
        GeminiClient(
            api_key=settings.gemini.api_key,
            model=settings.gemini.model,
        )
    )

    processed = 0
    updated = 0
    failures = 0
    for question in questions:
        processed += 1
        try:
            generated = explanation_service.generate_explanations(question)
            merged = explanation_service.merge_missing_explanations(question, generated)
            if args.dry_run:
                print(
                    f"[DRY-RUN] Question {question.id_question}: "
                    f"would enrich correct answer and {len(merged.wrong_answers)} wrong answers."
                )
                updated += 1
                continue

            question_repository.update_question_explanations(
                id_question=question.id_question,
                correct_answer=merged.correct_answer,
                wrong_answers=merged.wrong_answers,
            )
            updated += 1
            print(f"[OK] Enriched question {question.id_question}.")
        except Exception as exc:
            failures += 1
            print(f"[ERROR] Question {question.id_question}: {exc}")

    mode = "dry-run" if args.dry_run else "write"
    print(
        f"Processed {processed} question(s) in {mode} mode: "
        f"{updated} succeeded, {failures} failed."
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
