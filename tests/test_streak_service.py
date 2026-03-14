from datetime import date, datetime, timezone

from modules.domain.models import AnswerAttempt
from modules.services.streak_service import compute_day_streak, compute_question_streak


def _answer(
    *,
    id_answer: str,
    id_user: int,
    is_correct: bool,
    answered_at_utc: datetime,
    answered_at_local: datetime,
) -> AnswerAttempt:
    return AnswerAttempt(
        id_answer=id_answer,
        id_user=id_user,
        email="ana@example.com",
        id_question=1,
        selected_choice="A",
        correct_choice="A",
        is_correct=is_correct,
        answered_at_utc=answered_at_utc,
        answered_at_local=answered_at_local,
        time_spent_seconds=5.0,
        session_id="session-1",
    )


def test_compute_day_streak_counts_consecutive_days() -> None:
    answers = [
        _answer(
            id_answer="a1",
            id_user=1,
            is_correct=True,
            answered_at_utc=datetime(2026, 3, 7, 15, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 7, 12, 0),
        ),
        _answer(
            id_answer="a2",
            id_user=1,
            is_correct=True,
            answered_at_utc=datetime(2026, 3, 6, 15, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 6, 12, 0),
        ),
        _answer(
            id_answer="a3",
            id_user=1,
            is_correct=False,
            answered_at_utc=datetime(2026, 3, 5, 15, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 5, 12, 0),
        ),
    ]

    assert (
        compute_day_streak(
            answers,
            timezone_name="America/Sao_Paulo",
            today=date(2026, 3, 7),
        )
        == 3
    )


def test_compute_day_streak_drops_to_zero_after_gap() -> None:
    answers = [
        _answer(
            id_answer="a1",
            id_user=1,
            is_correct=True,
            answered_at_utc=datetime(2026, 3, 5, 15, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 5, 12, 0),
        )
    ]

    assert (
        compute_day_streak(
            answers,
            timezone_name="America/Sao_Paulo",
            today=date(2026, 3, 7),
        )
        == 0
    )


def test_compute_question_streak_stops_on_first_incorrect_answer() -> None:
    answers = [
        _answer(
            id_answer="a1",
            id_user=1,
            is_correct=True,
            answered_at_utc=datetime(2026, 3, 7, 15, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 7, 12, 0),
        ),
        _answer(
            id_answer="a2",
            id_user=1,
            is_correct=True,
            answered_at_utc=datetime(2026, 3, 7, 14, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 7, 11, 0),
        ),
        _answer(
            id_answer="a3",
            id_user=1,
            is_correct=False,
            answered_at_utc=datetime(2026, 3, 7, 13, 0, tzinfo=timezone.utc),
            answered_at_local=datetime(2026, 3, 7, 10, 0),
        ),
    ]

    assert compute_question_streak(answers) == 2
