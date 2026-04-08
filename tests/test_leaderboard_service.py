import pandas as pd

from datetime import datetime, timezone

from modules.domain.models import AnswerAttempt, User
from modules.services.leaderboard_service import (
    compute_leaderboard,
    find_user_position,
    format_position,
    parse_leaderboard_position_dataframe,
)


def _answer(id_answer: str, user_email: str, is_correct: bool) -> AnswerAttempt:
    timestamp = datetime(2026, 3, 7, 15, 0, tzinfo=timezone.utc)
    return AnswerAttempt(
        id_answer=id_answer,
        id_question=1,
        user_email=user_email,
        selected_alternative_text="4",
        correct_alternative_text="4",
        is_correct=is_correct,
        answered_at_utc=timestamp,
        answered_at_local=timestamp.replace(tzinfo=None),
        time_spent_seconds=4.0,
        session_id="session",
    )


def test_compute_leaderboard_orders_by_correct_then_answers_then_email() -> None:
    answers = [
        _answer("a1", "ana@example.com", True),
        _answer("a2", "ana@example.com", True),
        _answer("a3", "bia@example.com", True),
        _answer("a4", "bia@example.com", False),
    ]

    leaderboard = compute_leaderboard(answers)

    assert [entry.user_email for entry in leaderboard] == [
        "ana@example.com",
        "bia@example.com",
    ]
    assert format_position(
        find_user_position(leaderboard, User(email="bia@example.com", name="Bia")),
        len(leaderboard),
    ) == "#2 / 2"


def test_format_position_handles_missing_user() -> None:
    leaderboard = compute_leaderboard([_answer("a1", "ana@example.com", True)])

    assert find_user_position(leaderboard, User(email="cai@example.com")) is None
    assert format_position(None, len(leaderboard)) == "#- / 1"


def test_parse_leaderboard_position_dataframe_reads_rank_and_total_users() -> None:
    rank, total_users, issues = parse_leaderboard_position_dataframe(
        pd.DataFrame([{"rank": 3, "total_users": 17}])
    )

    assert issues == []
    assert rank == 3
    assert total_users == 17


def test_parse_leaderboard_position_dataframe_accepts_missing_rank_for_new_user() -> None:
    rank, total_users, issues = parse_leaderboard_position_dataframe(
        pd.DataFrame([{"rank": None, "total_users": 17}])
    )

    assert issues == []
    assert rank is None
    assert total_users == 17
