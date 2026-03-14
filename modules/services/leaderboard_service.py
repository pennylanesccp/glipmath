from __future__ import annotations

import pandas as pd

from modules.domain.models import AnswerAttempt, LeaderboardEntry, User
from modules.storage.schema_validation import prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.normalization import clean_optional_text, normalize_email

LEADERBOARD_RESOURCE_NAME = "v_leaderboard"
LEADERBOARD_REQUIRED_COLUMNS = [
    "rank",
    "id_user",
    "email",
    "display_name",
    "total_correct",
    "total_answers",
]


def compute_leaderboard(
    users: list[User],
    answers: list[AnswerAttempt],
) -> list[LeaderboardEntry]:
    """Compute leaderboard entries for all active whitelisted users."""

    active_users = [user for user in users if user.is_active]
    stats = {
        user.id_user: {
            "user": user,
            "total_correct": 0,
            "total_answers": 0,
        }
        for user in active_users
    }

    for answer in answers:
        if answer.id_user not in stats:
            continue
        stats[answer.id_user]["total_answers"] += 1
        if answer.is_correct:
            stats[answer.id_user]["total_correct"] += 1

    ordered = sorted(
        stats.values(),
        key=lambda item: (
            -item["total_correct"],
            -item["total_answers"],
            item["user"].email,
        ),
    )

    entries: list[LeaderboardEntry] = []
    for index, item in enumerate(ordered, start=1):
        user = item["user"]
        entries.append(
            LeaderboardEntry(
                rank=index,
                id_user=user.id_user,
                email=user.email,
                display_name=user.display_name,
                total_correct=item["total_correct"],
                total_answers=item["total_answers"],
            )
        )
    return entries


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
            email = normalize_email(str(row.get("email", "")))
            if not email:
                raise ValueError("email cannot be blank.")
            display_name = clean_optional_text(row.get("display_name")) or email
            entries.append(
                LeaderboardEntry(
                    rank=_parse_required_int(row.get("rank"), "rank"),
                    id_user=_parse_required_int(row.get("id_user"), "id_user"),
                    email=email,
                    display_name=display_name,
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
        if entry.id_user == user.id_user:
            return entry
    return None


def format_position(entry: LeaderboardEntry | None, total_users: int) -> str:
    """Format leaderboard position for UI metrics."""

    if entry is None or total_users == 0:
        return "#- / 0"
    return f"#{entry.rank} / {total_users}"


def _parse_required_int(value: object, field_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid integer.") from exc
