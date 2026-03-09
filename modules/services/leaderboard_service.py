from __future__ import annotations

from modules.domain.models import AnswerRecord, AppUser, LeaderboardEntry


def compute_leaderboard(
    users: list[AppUser],
    answers: list[AnswerRecord],
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


def find_user_position(
    leaderboard: list[LeaderboardEntry],
    user: AppUser,
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
