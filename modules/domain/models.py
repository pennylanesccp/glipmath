from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from modules.utils.datetime_utils import to_bigquery_datetime_string, to_iso_timestamp


@dataclass(frozen=True, slots=True)
class QuestionAlternative:
    """Canonical answer alternative stored in the question bank."""

    alternative_text: str
    explanation: str | None = None


@dataclass(frozen=True, slots=True)
class DisplayAlternative:
    """Alternative rendered to the learner after in-app randomization."""

    option_id: str
    alternative_text: str
    explanation: str | None
    is_correct: bool


@dataclass(frozen=True, slots=True)
class Question:
    """A validated question loaded from BigQuery."""

    id_question: int
    statement: str
    correct_answer: QuestionAlternative
    wrong_answers: tuple[QuestionAlternative, ...]
    subject: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    source: str | None = None
    created_at_utc: datetime | None = None
    updated_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class QuestionIndexEntry:
    """Lightweight active-question metadata used for selection and filtering."""

    id_question: int
    subject: str | None = None


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """Authenticated identity returned by Streamlit OIDC."""

    email: str
    name: str | None


@dataclass(frozen=True, slots=True)
class User:
    """Authenticated app user for the current MVP."""

    email: str
    name: str | None = None

    @property
    def display_name(self) -> str:
        """Return the preferred display name for the UI."""

        return self.name or self.email


@dataclass(frozen=True, slots=True)
class AnswerAttempt:
    """Append-only answer event persisted in BigQuery."""

    id_answer: str
    id_question: int
    user_email: str
    selected_alternative_text: str
    correct_alternative_text: str
    is_correct: bool
    answered_at_utc: datetime
    answered_at_local: datetime | None
    time_spent_seconds: float
    session_id: str
    subject: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    source: str | None = None
    app_version: str | None = None

    def to_bigquery_row(self) -> dict[str, object]:
        """Serialize the answer for BigQuery streaming inserts."""

        return {
            "id_answer": self.id_answer,
            "id_question": self.id_question,
            "user_email": self.user_email,
            "selected_alternative_text": self.selected_alternative_text,
            "correct_alternative_text": self.correct_alternative_text,
            "is_correct": self.is_correct,
            "answered_at_utc": to_iso_timestamp(self.answered_at_utc),
            "answered_at_local": to_bigquery_datetime_string(self.answered_at_local),
            "time_spent_seconds": round(self.time_spent_seconds, 2),
            "session_id": self.session_id,
            "subject": self.subject,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "source": self.source,
            "app_version": self.app_version,
        }


@dataclass(frozen=True, slots=True)
class AnswerEvaluation:
    """Result of evaluating and preparing an answer submission."""

    record: AnswerAttempt
    feedback_message: str
    correct_explanation: str | None = None
    selected_explanation: str | None = None


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """Aggregated user performance for leaderboard rendering."""

    rank: int
    user_email: str
    display_name: str
    total_correct: int
    total_answers: int
