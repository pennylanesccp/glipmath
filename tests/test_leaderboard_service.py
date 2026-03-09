from datetime import datetime, timezone

from modules.domain.models import AnswerRecord, AppUser
from modules.services.leaderboard_service import compute_leaderboard, find_user_position, format_position


def _answer(id_answer: int, id_user: int, is_correct: bool) -> AnswerRecord:
    timestamp = datetime(2026, 3, 7, 15, id_answer, tzinfo=timezone.utc)
    return AnswerRecord(
        id_answer=id_answer,
        id_user=id_user,
        email=f"user{id_user}@example.com",
        id_question=id_answer,
        selected_choice="A",
        correct_choice="A",
        is_correct=is_correct,
        answered_at_utc=timestamp,
        answered_at_local=timestamp,
        time_spent_seconds=4.0,
        session_id="session",
    )


def test_compute_leaderboard_orders_by_correct_then_answers_then_email() -> None:
    users = [
        AppUser(id_user=1, email="ana@example.com", name="Ana", is_active=True),
        AppUser(id_user=2, email="bia@example.com", name="Bia", is_active=True),
        AppUser(id_user=3, email="cai@example.com", name="Cai", is_active=True),
    ]
    answers = [
        _answer(1, 1, True),
        _answer(2, 1, True),
        _answer(3, 2, True),
        _answer(4, 2, False),
    ]

    leaderboard = compute_leaderboard(users, answers)

    assert [entry.id_user for entry in leaderboard] == [1, 2, 3]
    assert format_position(find_user_position(leaderboard, users[1]), len(leaderboard)) == "#2 / 3"


def test_compute_leaderboard_ignores_inactive_users() -> None:
    users = [
        AppUser(id_user=1, email="ana@example.com", is_active=True),
        AppUser(id_user=2, email="bia@example.com", is_active=False),
    ]
    answers = [_answer(1, 2, True)]

    leaderboard = compute_leaderboard(users, answers)

    assert len(leaderboard) == 1
    assert leaderboard[0].id_user == 1
