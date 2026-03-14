from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from modules.domain.models import AnswerAttempt
from modules.utils.datetime_utils import today_in_timezone


def compute_day_streak(
    answers: list[AnswerAttempt],
    *,
    timezone_name: str,
    today: date | None = None,
) -> int:
    """Compute consecutive active days ending on today or yesterday."""

    if not answers:
        return 0

    current_date = today or today_in_timezone(timezone_name)
    active_dates = {_answer_local_date(answer, timezone_name) for answer in answers}
    latest_activity = max(active_dates)

    if latest_activity == current_date:
        cursor = current_date
    elif latest_activity == current_date - timedelta(days=1):
        cursor = latest_activity
    else:
        return 0

    streak = 0
    while cursor in active_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_question_streak(answers: list[AnswerAttempt]) -> int:
    """Compute the current consecutive correct-answer streak."""

    ordered_answers = sorted(answers, key=lambda answer: answer.answered_at_utc, reverse=True)
    streak = 0
    for answer in ordered_answers:
        if not answer.is_correct:
            break
        streak += 1
    return streak


def _answer_local_date(answer: AnswerAttempt, timezone_name: str) -> date:
    if answer.answered_at_local is not None:
        return answer.answered_at_local.date()
    return answer.answered_at_utc.astimezone(ZoneInfo(timezone_name)).date()
