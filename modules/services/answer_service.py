from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pandas as pd

from modules.domain.models import AnswerAttempt, AnswerEvaluation, DisplayAlternative, Question, User, UserProgressSnapshot
from modules.storage.schema_validation import iter_dataframe_rows, prepare_dataframe, require_columns, worksheet_row_number
from modules.utils.datetime_utils import parse_local_datetime, parse_timestamp, utc_now
from modules.utils.id_utils import generate_answer_id
from modules.utils.normalization import clean_optional_text, normalize_email

if TYPE_CHECKING:
    from modules.storage.answer_repository import AnswerRepository

ANSWERS_RESOURCE_NAME = "answers"
ANSWERS_REQUIRED_COLUMNS = [
    "id_answer",
    "id_question",
    "user_email",
    "selected_alternative_text",
    "correct_alternative_text",
    "is_correct",
    "answered_at_utc",
    "answered_at_local",
    "time_spent_seconds",
    "session_id",
]
USER_PROGRESS_RESOURCE_NAME = "answers_progress"
USER_PROGRESS_REQUIRED_COLUMNS = [
    "answered_question_ids",
    "activity_dates",
    "question_streak",
]


@dataclass(slots=True)
class AnswerService:
    """Handle answer evaluation and persistence."""

    answer_repository: "AnswerRepository"
    timezone_name: str
    app_version: str

    def submit_answer(
        self,
        *,
        user: User,
        question: Question,
        selected_alternative: DisplayAlternative,
        session_id: str,
        time_spent_seconds: float,
    ) -> AnswerEvaluation:
        """Evaluate an answer and append a new answer log row."""

        evaluation = build_answer_evaluation(
            user=user,
            question=question,
            selected_alternative=selected_alternative,
            session_id=session_id,
            time_spent_seconds=time_spent_seconds,
            timezone_name=self.timezone_name,
            app_version=self.app_version,
        )
        self.answer_repository.append_answer_row(evaluation.record.to_bigquery_row())
        return evaluation


def append_answer_history(
    answers: Sequence[AnswerAttempt],
    new_answer: AnswerAttempt,
) -> list[AnswerAttempt]:
    """Prepend a newly submitted answer if it is not already present."""

    if any(answer.id_answer == new_answer.id_answer for answer in answers):
        return list(answers)
    return [new_answer, *answers]


def extract_answered_question_ids(answers: Sequence[AnswerAttempt]) -> set[int]:
    """Return the unique answered question identifiers from answer history."""

    return {answer.id_question for answer in answers}


def parse_answers_dataframe(dataframe: pd.DataFrame) -> tuple[list[AnswerAttempt], list[str]]:
    """Parse answer history, tolerating empty tables for new deployments."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, ANSWERS_REQUIRED_COLUMNS, ANSWERS_RESOURCE_NAME)

    answers: list[AnswerAttempt] = []
    issues: list[str] = []
    for index, row in iter_dataframe_rows(prepared):
        if _is_blank_row(row):
            continue

        row_number = worksheet_row_number(index)
        try:
            answered_at_utc = parse_timestamp(row.get("answered_at_utc"))
            if answered_at_utc is None:
                raise ValueError("answered_at_utc must be a valid timestamp.")
            answers.append(
                AnswerAttempt(
                    id_answer=_parse_required_text(row.get("id_answer"), "id_answer"),
                    id_question=_parse_required_int(row.get("id_question"), "id_question"),
                    user_email=normalize_email(_parse_required_text(row.get("user_email"), "user_email")),
                    selected_alternative_text=_parse_required_text(
                        row.get("selected_alternative_text"),
                        "selected_alternative_text",
                    ),
                    correct_alternative_text=_parse_required_text(
                        row.get("correct_alternative_text"),
                        "correct_alternative_text",
                    ),
                    is_correct=_parse_bool(row.get("is_correct")),
                    answered_at_utc=answered_at_utc,
                    answered_at_local=parse_local_datetime(row.get("answered_at_local")),
                    time_spent_seconds=float(row.get("time_spent_seconds", 0) or 0),
                    session_id=_parse_required_text(row.get("session_id"), "session_id"),
                    subject=clean_optional_text(row.get("subject")),
                    topic=clean_optional_text(row.get("topic")),
                    difficulty=clean_optional_text(row.get("difficulty")),
                    source=clean_optional_text(row.get("source")),
                    cohort_key=clean_optional_text(row.get("cohort_key")),
                    app_version=clean_optional_text(row.get("app_version")),
                )
            )
        except ValueError as exc:
            issues.append(f"{ANSWERS_RESOURCE_NAME} row {row_number}: {exc}")

    return answers, issues


def parse_user_progress_snapshot_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[UserProgressSnapshot, list[str]]:
    """Parse one compact user-progress snapshot row returned by BigQuery."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return UserProgressSnapshot(), []

    require_columns(prepared, USER_PROGRESS_REQUIRED_COLUMNS, USER_PROGRESS_RESOURCE_NAME)

    issues: list[str] = []
    if len(prepared.index) > 1:
        issues.append("answers_progress query returned more than one row for a single user snapshot.")

    row = prepared.iloc[0].to_dict()
    row_number = worksheet_row_number(prepared.index[0])
    try:
        snapshot = UserProgressSnapshot(
            answered_question_ids=tuple(
                sorted(
                    {
                        _parse_required_int(item, "answered_question_ids[]")
                        for item in _parse_array_value(row.get("answered_question_ids"), "answered_question_ids")
                    }
                )
            ),
            activity_dates=tuple(
                sorted(
                    {
                        _parse_activity_date(item, "activity_dates[]")
                        for item in _parse_array_value(row.get("activity_dates"), "activity_dates")
                    },
                    reverse=True,
                )
            ),
            question_streak=max(_parse_required_int(row.get("question_streak"), "question_streak"), 0),
        )
    except ValueError as exc:
        issues.append(f"{USER_PROGRESS_RESOURCE_NAME} row {row_number}: {exc}")
        snapshot = UserProgressSnapshot()
    return snapshot, issues


def build_answer_evaluation(
    *,
    user: User,
    question: Question,
    selected_alternative: DisplayAlternative,
    session_id: str,
    time_spent_seconds: float,
    timezone_name: str,
    app_version: str,
) -> AnswerEvaluation:
    """Build a validated answer record and user-facing feedback message."""

    _ensure_selected_alternative_matches_question(question, selected_alternative)

    answered_at_utc = utc_now()
    answered_at_local = answered_at_utc.astimezone(ZoneInfo(timezone_name)).replace(tzinfo=None)
    is_correct = selected_alternative.is_correct

    record = AnswerAttempt(
        id_answer=generate_answer_id(),
        id_question=question.id_question,
        user_email=user.email,
        selected_alternative_text=selected_alternative.alternative_text,
        correct_alternative_text=question.correct_answer.alternative_text,
        is_correct=is_correct,
        answered_at_utc=answered_at_utc,
        answered_at_local=answered_at_local,
        time_spent_seconds=max(float(time_spent_seconds), 0.0),
        session_id=session_id,
        subject=question.subject,
        topic=question.topic,
        difficulty=question.difficulty,
        source=question.source,
        cohort_key=question.cohort_key,
        app_version=app_version,
    )
    return AnswerEvaluation(
        record=record,
        feedback_message="Resposta correta." if is_correct else "Resposta incorreta.",
        correct_explanation=question.correct_answer.explanation,
        selected_explanation=selected_alternative.explanation if not is_correct else None,
    )


def _ensure_selected_alternative_matches_question(
    question: Question,
    selected_alternative: DisplayAlternative,
) -> None:
    valid_texts = {
        question.correct_answer.alternative_text,
        *(wrong_answer.alternative_text for wrong_answer in question.wrong_answers),
    }
    if selected_alternative.alternative_text not in valid_texts:
        raise ValueError("selected alternative does not belong to the current question.")


def _parse_required_int(value: object, field_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid integer.") from exc


def _parse_required_text(value: object, field_name: str) -> str:
    text = clean_optional_text(value)
    if not text:
        raise ValueError(f"{field_name} cannot be blank.")
    return text


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("is_correct must be a boolean-like value.")


def _is_blank_row(row: dict[str, object]) -> bool:
    return all(not str(value).strip() for value in row.values())


def _parse_array_value(value: object, field_name: str) -> list[object]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return converted
        if isinstance(converted, tuple):
            return list(converted)
    raise ValueError(f"{field_name} must be an array-like value.")


def _parse_activity_date(value: object, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be a valid date.")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid date.") from exc
