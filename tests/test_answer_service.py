from datetime import datetime, timezone

import pandas as pd
import pytest

from modules.domain.models import DisplayAlternative, Question, QuestionAlternative, User
from modules.services.answer_service import build_answer_evaluation, parse_answers_dataframe


def test_build_answer_evaluation_marks_correct_answer() -> None:
    question = Question(
        id_question=1,
        statement="Quanto e 2 + 2?",
        correct_answer=QuestionAlternative("4", "Explicacao correta."),
        wrong_answers=(QuestionAlternative("3", "Explicacao incorreta."),),
        subject="matematica",
        topic="aritmetica",
        difficulty="facil",
        source="seed",
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
                "app_version": "0.1.0",
            }
        ]
    )

    answers, issues = parse_answers_dataframe(frame)

    assert not issues
    assert answers[0].user_email == "ana@example.com"
    assert answers[0].selected_alternative_text == "3"
    assert answers[0].subject == "matematica"
