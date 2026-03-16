from __future__ import annotations

import json
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from modules.domain.models import DisplayAlternative, Question, QuestionAlternative
from modules.storage.schema_validation import (
    ensure_unique_integer_values,
    prepare_dataframe,
    require_columns,
    worksheet_row_number,
)
from modules.utils.datetime_utils import parse_timestamp
from modules.utils.normalization import clean_optional_text, coerce_bool

QUESTION_RESOURCE_NAME = "question_bank"
QUESTION_REQUIRED_COLUMNS = [
    "id_question",
    "statement",
    "correct_answer",
    "wrong_answers",
]


@dataclass(frozen=True, slots=True)
class QuestionRowIssue:
    """Validation issue tied to one canonical question-bank row."""

    row_index: int
    row_number: int
    message: str


def parse_question_bank_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[Question], list[str]]:
    """Parse and validate nested question bank rows."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, QUESTION_REQUIRED_COLUMNS, QUESTION_RESOURCE_NAME)
    ensure_unique_integer_values(prepared, "id_question", QUESTION_RESOURCE_NAME)

    questions: list[Question] = []
    issues: list[str] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        try:
            question = _parse_question_row(row.to_dict())
        except ValueError as exc:
            issues.append(f"{QUESTION_RESOURCE_NAME} row {row_number}: {exc}")
            continue
        if question is not None:
            questions.append(question)
    return questions, issues


def find_valid_question_bank_row_indexes(
    rows: Sequence[dict[str, object]],
) -> tuple[list[int], list[QuestionRowIssue]]:
    """Return the canonical row indexes that can be safely loaded."""

    prepared = prepare_dataframe(pd.DataFrame(rows))
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, QUESTION_REQUIRED_COLUMNS, QUESTION_RESOURCE_NAME)

    duplicate_id_by_index = _find_duplicate_id_by_index(prepared)
    valid_indexes: list[int] = []
    issues: list[QuestionRowIssue] = []
    for index, row in prepared.iterrows():
        row_number = worksheet_row_number(index)
        duplicate_id = duplicate_id_by_index.get(index)
        if duplicate_id is not None:
            issues.append(
                QuestionRowIssue(
                    row_index=index,
                    row_number=row_number,
                    message=f"id_question must be unique; duplicate value {duplicate_id}.",
                )
            )
            continue

        try:
            _parse_question_row(row.to_dict())
        except ValueError as exc:
            issues.append(
                QuestionRowIssue(
                    row_index=index,
                    row_number=row_number,
                    message=str(exc),
                )
            )
            continue

        valid_indexes.append(index)

    return valid_indexes, issues


def select_next_question(
    questions: Iterable[Question],
    answered_question_ids: set[int],
    *,
    randomizer: random.Random | None = None,
) -> Question | None:
    """Select the next question, prioritizing unseen active questions first."""

    available_questions = list(questions)
    if not available_questions:
        return None

    unseen_questions = [
        question
        for question in available_questions
        if question.id_question not in answered_question_ids
    ]
    pool = unseen_questions or available_questions
    chooser = randomizer or random.Random()
    ordered_pool = sorted(pool, key=lambda question: question.id_question)
    return chooser.choice(ordered_pool)


def find_question_by_id(
    questions: Iterable[Question],
    id_question: int | None,
) -> Question | None:
    """Return a question by ID."""

    if id_question is None:
        return None
    for question in questions:
        if question.id_question == id_question:
            return question
    return None


def build_display_alternatives(
    question: Question,
    *,
    randomizer: random.Random | None = None,
) -> list[DisplayAlternative]:
    """Build and randomize display alternatives for a question."""

    alternatives = [
        DisplayAlternative(
            option_id="correct",
            alternative_text=question.correct_answer.alternative_text,
            explanation=question.correct_answer.explanation,
            is_correct=True,
        )
    ]
    for index, wrong_answer in enumerate(question.wrong_answers, start=1):
        alternatives.append(
            DisplayAlternative(
                option_id=f"wrong_{index}",
                alternative_text=wrong_answer.alternative_text,
                explanation=wrong_answer.explanation,
                is_correct=False,
            )
        )

    chooser = randomizer or random.Random()
    shuffled = list(alternatives)
    chooser.shuffle(shuffled)
    return shuffled


def find_display_alternative(
    alternatives: Sequence[DisplayAlternative],
    option_id: str | None,
) -> DisplayAlternative | None:
    """Return the selected display alternative by option ID."""

    if not option_id:
        return None
    for alternative in alternatives:
        if alternative.option_id == option_id:
            return alternative
    return None


def _parse_question_row(row: dict[str, object]) -> Question | None:
    id_question = _parse_required_int(row.get("id_question"), "id_question")
    is_active = coerce_bool(row.get("is_active"), default=True)
    if not is_active:
        return None

    statement = _parse_required_text(row.get("statement"), "statement")
    correct_answer = _parse_alternative(row.get("correct_answer"), field_name="correct_answer")
    wrong_answers = _parse_wrong_answers(row.get("wrong_answers"))
    _ensure_unique_alternative_texts(correct_answer, wrong_answers)

    return Question(
        id_question=id_question,
        statement=statement,
        correct_answer=correct_answer,
        wrong_answers=wrong_answers,
        subject=clean_optional_text(row.get("subject")),
        topic=clean_optional_text(row.get("topic")),
        difficulty=clean_optional_text(row.get("difficulty")),
        source=clean_optional_text(row.get("source")),
        created_at_utc=parse_timestamp(row.get("created_at_utc")),
        updated_at_utc=parse_timestamp(row.get("updated_at_utc")),
    )


def _parse_wrong_answers(value: object) -> tuple[QuestionAlternative, ...]:
    parsed = _parse_jsonish_value(value, expected_type=list, field_name="wrong_answers")
    wrong_answers = tuple(
        _parse_alternative(item, field_name=f"wrong_answers[{index}]")
        for index, item in enumerate(parsed)
    )
    if not wrong_answers:
        raise ValueError("wrong_answers must contain at least one alternative.")
    return wrong_answers


def _parse_alternative(value: object, *, field_name: str) -> QuestionAlternative:
    parsed = _parse_jsonish_value(value, expected_type=dict, field_name=field_name)
    alternative_text = _parse_required_text(
        parsed.get("alternative_text"),
        f"{field_name}.alternative_text",
    )
    return QuestionAlternative(
        alternative_text=alternative_text,
        explanation=clean_optional_text(parsed.get("explanation")),
    )


def _parse_jsonish_value(value: object, *, expected_type: type, field_name: str) -> Any:
    if isinstance(value, expected_type):
        return value
    if value is None:
        raise ValueError(f"{field_name} cannot be blank.")

    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} cannot be blank.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON-like data.") from exc

    if not isinstance(parsed, expected_type):
        raise ValueError(f"{field_name} has an invalid nested structure.")
    return parsed


def _ensure_unique_alternative_texts(
    correct_answer: QuestionAlternative,
    wrong_answers: Sequence[QuestionAlternative],
) -> None:
    seen: set[str] = set()
    for alternative in (correct_answer, *wrong_answers):
        normalized = alternative.alternative_text.strip().lower()
        if normalized in seen:
            raise ValueError("alternative_text values must be unique within a question.")
        seen.add(normalized)


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


def _find_duplicate_id_by_index(dataframe: pd.DataFrame) -> dict[int, int]:
    ids_by_index: dict[int, int] = {}
    row_indexes_by_id: dict[int, list[int]] = {}

    for index, row in dataframe.iterrows():
        try:
            parsed_id = int(str(row.get("id_question")).strip())
        except (TypeError, ValueError):
            continue

        ids_by_index[index] = parsed_id
        row_indexes_by_id.setdefault(parsed_id, []).append(index)

    duplicates: dict[int, int] = {}
    for parsed_id, row_indexes in row_indexes_by_id.items():
        if len(row_indexes) < 2:
            continue
        for row_index in row_indexes:
            duplicates[row_index] = ids_by_index[row_index]

    return duplicates
