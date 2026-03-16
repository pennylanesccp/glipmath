from __future__ import annotations

import pandas as pd

from modules.domain.models import AnswerAttempt, LeaderboardEntry, User
from modules.storage.schema_validation import prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.normalization import clean_optional_text, normalize_email

LEADERBOARD_RESOURCE_NAME = "v_leaderboard"
LEADERBOARD_REQUIRED_COLUMNS = [
    "rank",
    "user_email",
    "display_name",
    "total_correct",
    "total_answers",
]


def compute_leaderboard(
    answers: list[AnswerAttempt],
) -> list[LeaderboardEntry]:
    """Compute leaderboard entries from append-only answer events."""

    stats: dict[str, dict[str, int | str]] = {}
    for answer in answers:
        if answer.user_email not in stats:
            stats[answer.user_email] = {
                "user_email": answer.user_email,
                "display_name": answer.user_email,
                "total_correct": 0,
                "total_answers": 0,
            }
        stats[answer.user_email]["total_answers"] += 1
        if answer.is_correct:
            stats[answer.user_email]["total_correct"] += 1

    ordered = sorted(
        stats.values(),
        key=lambda item: (
            -int(item["total_correct"]),
            -int(item["total_answers"]),
            str(item["user_email"]),
        ),
    )

    return [
        LeaderboardEntry(
            rank=index,
            user_email=str(item["user_email"]),
            display_name=str(item["display_name"]),
            total_correct=int(item["total_correct"]),
            total_answers=int(item["total_answers"]),
        )
        for index, item in enumerate(ordered, start=1)
    ]


def parse_leaderboard_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[LeaderboardEntry], list[str]]:
    """Parse leaderboard view rows."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, LEADERBOARD_REQUIRED_COLUMNS, LEADERBOARD_RESOURCE_NAME)

    entries: list[LeaderboardEntry] = []
    issues: list[str] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        try:
            user_email = normalize_email(str(row.get("user_email", "")))
            if not user_email:
                raise ValueError("user_email cannot be blank.")
            entries.append(
                LeaderboardEntry(
                    rank=_parse_required_int(row.get("rank"), "rank"),
                    user_email=user_email,
                    display_name=clean_optional_text(row.get("display_name")) or user_email,
                    total_correct=_parse_required_int(row.get("total_correct"), "total_correct"),
                    total_answers=_parse_required_int(row.get("total_answers"), "total_answers"),
                )
            )
        except ValueError as exc:
            issues.append(f"{LEADERBOARD_RESOURCE_NAME} row {row_number}: {exc}")

    entries.sort(key=lambda entry: entry.rank)
    return entries, issues


def find_user_position(
    leaderboard: list[LeaderboardEntry],
    user: User,
) -> LeaderboardEntry | None:
    """Find the leaderboard entry for the given user."""

    for entry in leaderboard:
        if entry.user_email == user.email:
            return entry
    return None


def format_position(entry: LeaderboardEntry | None, total_users: int) -> str:
    """Format leaderboard position for UI metrics."""

    if total_users == 0:
        return "#- / 0"
    if entry is None:
        return f"#- / {total_users}"
    return f"#{entry.rank} / {total_users}"


def _parse_required_int(value: object, field_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid integer.") from exc
