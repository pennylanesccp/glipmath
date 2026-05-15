from datetime import date, datetime, timezone

import pandas as pd
import pytest

from modules.domain.models import DisplayAlternative, Question, QuestionAlternative, User, UserProgressSnapshot
from modules.services.answer_service import (
    append_answer_history,
    build_answer_evaluation,
    extract_answered_question_ids,
    parse_answers_dataframe,
    parse_user_progress_snapshot_dataframe,
)


def test_build_answer_evaluation_marks_correct_answer() -> None:
    question = Question(
        id_question=1,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4", "Explicacao correta."),
        wrong_answers=(QuestionAlternative("3", "Explicacao incorreta."),),
        subject="matematica",
        topic="aritmetica",
        difficulty=2,
        source="seed",
        cohort_key="ano_1",
    )

    evaluation = build_answer_evaluation(
        user=User(email="ana@example.com", name="Ana"),
        question=question,
        selected_alternative=DisplayAlternative(
            option_id="correct",
            alternative_text="4",
            explanation="Explicacao correta.",
            is_correct=True,
        ),
        session_id="session-1",
        time_spent_seconds=4.2,
        timezone_name="America/Sao_Paulo",
        app_version="0.1.0",
    )

    assert evaluation.record.user_email == "ana@example.com"
    assert evaluation.record.is_correct is True
    assert evaluation.record.correct_alternative_text == "4"
    assert evaluation.record.subject == "matematica"
    assert evaluation.record.difficulty == "2"
    assert evaluation.record.cohort_key == "ano_1"
    assert evaluation.correct_explanation == "Explicacao correta."
    assert evaluation.selected_explanation is None


def test_build_answer_evaluation_rejects_foreign_alternative() -> None:
    question = Question(
        id_question=1,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4"),
        wrong_answers=(QuestionAlternative("3"),),
    )

    with pytest.raises(ValueError):
        build_answer_evaluation(
            user=User(email="ana@example.com"),
            question=question,
            selected_alternative=DisplayAlternative(
                option_id="wrong_9",
                alternative_text="999",
                explanation=None,
                is_correct=False,
            ),
            session_id="session-1",
            time_spent_seconds=4.2,
            timezone_name="America/Sao_Paulo",
            app_version="0.1.0",
        )


def test_parse_answers_dataframe_reads_new_answer_schema() -> None:
    frame = pd.DataFrame(
        [
            {
                "id_answer": "a1",
                "id_question": 1,
                "user_email": " ANA@example.com ",
                "selected_alternative_text": "3",
                "correct_alternative_text": "4",
                "is_correct": False,
                "answered_at_utc": datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
                "answered_at_local": datetime(2026, 3, 14, 9, 0),
                "time_spent_seconds": 5.5,
                "session_id": "session-1",
                "subject": "matematica",
                "topic": "aritmetica",
                "difficulty": "facil",
                "source": "seed",
                "cohort_key": "ano_1",
                "app_version": "0.1.0",
            }
        ]
    )

    answers, issues = parse_answers_dataframe(frame)

    assert not issues
    assert answers[0].user_email == "ana@example.com"
    assert answers[0].selected_alternative_text == "3"
    assert answers[0].subject == "matematica"
    assert answers[0].cohort_key == "ano_1"


def test_append_answer_history_prepends_and_deduplicates() -> None:
    existing_answer = parse_answers_dataframe(
        pd.DataFrame(
            [
                {
                    "id_answer": "a1",
                    "id_question": 1,
                    "user_email": "ana@example.com",
                    "selected_alternative_text": "3",
                    "correct_alternative_text": "4",
                    "is_correct": False,
                    "answered_at_utc": datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
                    "answered_at_local": datetime(2026, 3, 14, 9, 0),
                    "time_spent_seconds": 5.5,
                    "session_id": "session-1",
                }
            ]
        )
    )[0][0]
    new_answer = parse_answers_dataframe(
        pd.DataFrame(
            [
                {
                    "id_answer": "a2",
                    "id_question": 2,
                    "user_email": "ana@example.com",
                    "selected_alternative_text": "5",
                    "correct_alternative_text": "5",
                    "is_correct": True,
                    "answered_at_utc": datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc),
                    "answered_at_local": datetime(2026, 3, 14, 9, 5),
                    "time_spent_seconds": 4.2,
                    "session_id": "session-1",
                }
            ]
        )
    )[0][0]

    combined_answers = append_answer_history([existing_answer], new_answer)
    deduplicated_answers = append_answer_history(combined_answers, new_answer)

    assert [answer.id_answer for answer in combined_answers] == ["a2", "a1"]
    assert [answer.id_answer for answer in deduplicated_answers] == ["a2", "a1"]
    assert extract_answered_question_ids(deduplicated_answers) == {1, 2}


def test_parse_user_progress_snapshot_dataframe_reads_compact_snapshot() -> None:
    frame = pd.DataFrame(
        [
            {
                "answered_question_ids": [7, 2, 7],
                "activity_dates": [date(2026, 3, 23), "2026-03-22", datetime(2026, 3, 21, 9, 0)],
                "question_streak": 4,
            }
        ]
    )

    snapshot, issues = parse_user_progress_snapshot_dataframe(frame)

    assert issues == []
    assert snapshot == UserProgressSnapshot(
        answered_question_ids=(2, 7),
        activity_dates=(date(2026, 3, 23), date(2026, 3, 22), date(2026, 3, 21)),
        question_streak=4,
    )


def test_parse_user_progress_snapshot_dataframe_reports_invalid_payload() -> None:
    frame = pd.DataFrame(
        [
            {
                "answered_question_ids": "not-an-array",
                "activity_dates": [],
                "question_streak": 1,
            }
        ]
    )

    snapshot, issues = parse_user_progress_snapshot_dataframe(frame)

    assert snapshot == UserProgressSnapshot()
    assert issues == ["answers_progress row 2: answered_question_ids must be an array-like value."]
