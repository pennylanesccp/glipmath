from __future__ import annotations

import random
from collections.abc import Iterable

import pandas as pd

from modules.domain.models import Question
from modules.storage.schema_validation import (
    ensure_unique_integer_values,
    prepare_dataframe,
    require_columns,
    worksheet_row_number,
)
from modules.utils.datetime_utils import parse_timestamp
from modules.utils.normalization import clean_optional_text, coerce_bool, normalize_choice

QUESTION_RESOURCE_NAME = "question_bank"
QUESTION_REQUIRED_COLUMNS = [
    "id_question",
    "source",
    "statement",
    "choice_a",
    "choice_b",
    "choice_c",
    "choice_d",
    "correct_choice",
]


def parse_question_bank_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[Question], list[str]]:
    """Parse and validate question bank rows, skipping malformed inactive entries."""

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


def _parse_question_row(row: dict[str, object]) -> Question | None:
    id_question = _parse_required_int(row.get("id_question"), "id_question")
    is_active = coerce_bool(row.get("is_active"), default=True)
    if not is_active:
        return None

    source = _parse_required_text(row.get("source"), "source")
    statement = _parse_required_text(row.get("statement"), "statement")
    choices = _parse_choices(row)
    correct_choice = normalize_choice(str(row.get("correct_choice", "")))
    if correct_choice not in choices:
        raise ValueError("correct_choice must reference one of the populated alternatives A-E.")

    return Question(
        id_question=id_question,
        source=source,
        statement=statement,
        choices=choices,
        correct_choice=correct_choice,
        topic=clean_optional_text(row.get("topic")),
        difficulty=clean_optional_text(row.get("difficulty")),
        explanation=clean_optional_text(row.get("explanation")),
        created_at_utc=parse_timestamp(row.get("created_at_utc")),
        updated_at_utc=parse_timestamp(row.get("updated_at_utc")),
    )


def _parse_choices(row: dict[str, object]) -> dict[str, str]:
    labels = ["A", "B", "C", "D", "E"]
    choice_columns = ["choice_a", "choice_b", "choice_c", "choice_d", "choice_e"]
    choices: dict[str, str] = {}
    for label, column_name in zip(labels, choice_columns):
        text = clean_optional_text(row.get(column_name))
        if label in {"A", "B", "C", "D"} and not text:
            raise ValueError(f"{column_name} is required for active questions.")
        if text:
            choices[label] = text
    return choices


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
