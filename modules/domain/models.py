from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Question:
    """A validated multiple-choice math question."""

    id_question: int
    source: str
    statement: str
    choices: dict[str, str]
    correct_choice: str
    topic: str | None = None
    difficulty: str | None = None
    explanation: str | None = None

    def available_choices(self) -> list[tuple[str, str]]:
        """Return ordered choices for rendering."""

        return sorted(self.choices.items(), key=lambda item: item[0])


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """Authenticated identity returned by Streamlit OIDC."""

    email: str
    name: str | None


@dataclass(frozen=True, slots=True)
class AppUser:
    """User authorized to use the application."""

    id_user: int
    email: str
    name: str | None = None
    is_active: bool = True

    @property
    def display_name(self) -> str:
        """Return the preferred display name for the UI."""

        return self.name or self.email


@dataclass(frozen=True, slots=True)
class AnswerRecord:
    """Append-only answer event stored in Google Sheets."""

    id_answer: int
    id_user: int
    email: str
    id_question: int
    selected_choice: str
    correct_choice: str
    is_correct: bool
    answered_at_utc: datetime
    answered_at_local: datetime | None
    time_spent_seconds: float
    session_id: str
    source: str | None = None
    topic: str | None = None
    app_version: str | None = None

    def to_row(self) -> dict[str, object]:
        """Serialize the answer for worksheet appends."""

        return {
            "id_answer": self.id_answer,
            "id_user": self.id_user,
            "email": self.email,
            "id_question": self.id_question,
            "selected_choice": self.selected_choice,
            "correct_choice": self.correct_choice,
            "is_correct": str(self.is_correct).lower(),
            "answered_at_utc": self.answered_at_utc.isoformat(),
            "answered_at_local": self.answered_at_local.isoformat() if self.answered_at_local else "",
            "time_spent_seconds": round(self.time_spent_seconds, 2),
            "session_id": self.session_id,
            "source": self.source or "",
            "topic": self.topic or "",
            "app_version": self.app_version or "",
        }


@dataclass(frozen=True, slots=True)
class AnswerEvaluation:
    """Result of evaluating and preparing an answer submission."""

    record: AnswerRecord
    feedback_message: str


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """Aggregated user performance for leaderboard rendering."""

    rank: int
    id_user: int
    email: str
    display_name: str
    total_correct: int
    total_answers: int
