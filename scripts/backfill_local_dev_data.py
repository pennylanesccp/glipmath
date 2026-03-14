from __future__ import annotations

import argparse
import random
import sys
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.config.settings import load_settings
from modules.domain.models import AnswerAttempt
from modules.services.question_service import parse_question_bank_dataframe
from modules.services.user_service import list_active_users, parse_whitelist_dataframe
from modules.storage.bigquery_client import BigQueryClient
from modules.storage.question_repository import QuestionRepository
from modules.storage.whitelist_repository import WhitelistRepository
from modules.utils.datetime_utils import utc_now
from modules.utils.id_utils import generate_answer_id


def main() -> None:
    """Insert small synthetic answer history for local or dev testing."""

    parser = argparse.ArgumentParser(description="Backfill demo answers in BigQuery.")
    parser.add_argument("--project-id", default="ide-math-app")
    parser.add_argument("--region", default="southamerica-east1")
    parser.add_argument("--core-dataset", default="glipmath_core")
    parser.add_argument("--events-dataset", default="glipmath_events")
    parser.add_argument("--answers-table", default="answers")
    parser.add_argument("--count-per-user", type=int, default=3)
    args = parser.parse_args()

    settings = load_settings()
    bigquery_client = BigQueryClient(project_id=args.project_id, location=args.region)
    question_repository = QuestionRepository(
        bigquery_client,
        f"{args.project_id}.{args.core_dataset}.{settings.bigquery.question_bank_table}",
    )
    whitelist_repository = WhitelistRepository(
        bigquery_client,
        f"{args.project_id}.{args.core_dataset}.{settings.bigquery.whitelist_table}",
    )

    questions, question_issues = parse_question_bank_dataframe(question_repository.load_frame())
    users, user_issues = parse_whitelist_dataframe(whitelist_repository.load_frame())
    if question_issues or user_issues:
        for issue in question_issues + user_issues:
            print(f"[ERROR] {issue}")
        raise SystemExit(1)

    active_users = list_active_users(users)
    if not active_users or not questions:
        raise SystemExit("Need at least one active user and one active question to backfill data.")

    randomizer = random.Random(42)
    rows: list[dict[str, object]] = []
    now_utc = utc_now()
    timezone_name = settings.timezone
    for user in active_users:
        sampled_questions = randomizer.sample(questions, k=min(args.count_per_user, len(questions)))
        for offset, question in enumerate(sampled_questions, start=1):
            is_correct = offset % 2 == 1
            selected_choice = question.correct_choice
            if not is_correct:
                wrong_choices = [label for label in question.choices if label != question.correct_choice]
                selected_choice = wrong_choices[0]

            answered_at_utc = now_utc - timedelta(days=offset - 1, minutes=user.id_user)
            answered_at_local = (
                answered_at_utc.astimezone(ZoneInfo(timezone_name)).replace(tzinfo=None)
            )
            attempt = AnswerAttempt(
                id_answer=generate_answer_id(),
                id_user=user.id_user,
                email=user.email,
                id_question=question.id_question,
                selected_choice=selected_choice,
                correct_choice=question.correct_choice,
                is_correct=is_correct,
                answered_at_utc=answered_at_utc,
                answered_at_local=answered_at_local,
                time_spent_seconds=round(8 + offset * 1.5, 2),
                session_id=f"backfill-{user.id_user}",
                source=question.source,
                topic=question.topic,
                app_version=settings.app_version,
            )
            rows.append(attempt.to_bigquery_row())

    bigquery_client.insert_rows_json(
        f"{args.project_id}.{args.events_dataset}.{args.answers_table}",
        rows,
    )
    print(f"Inserted {len(rows)} synthetic answer row(s).")


if __name__ == "__main__":
    main()
