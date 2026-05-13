from __future__ import annotations

import json
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from modules.domain.models import DisplayAlternative, Question, QuestionAlternative, QuestionIndexEntry
from modules.storage.schema_validation import (
    ensure_unique_integer_values,
    iter_dataframe_rows,
    prepare_dataframe,
    require_columns,
    worksheet_row_number,
)
from modules.utils.datetime_utils import parse_timestamp
from modules.utils.normalization import clean_optional_text, coerce_bool, normalize_taxonomy_value

QUESTION_RESOURCE_NAME = "question_bank"
QUESTION_REQUIRED_COLUMNS = [
    "id_question",
    "statement",
    "correct_answer",
    "wrong_answers",
]
PROJECT_LABEL_BY_KEY = {
    "certificacao_databricks": "Certificação Databricks",
    "crescer_e_conectar": "Crescer e Conectar",
    "rumo_etec": "Rumo à ETEC",
}
SUBJECT_LABEL_BY_KEY = {
    "ciencias": "Ciências",
    "databricks": "Databricks",
    "geografia": "Geografia",
    "historia": "História",
    "matematica": "Matemática",
    "portugues": "Português",
    "todas": "Tudo",
}
TOPIC_LABEL_BY_KEY = {
    "autoloader e pipelines declarativas": "Data Ingestion & Acquisition",
    "delta otimizacao e storage": "Cost & Performance Optimisation",
    "delta sharing e federation": "Data Sharing and Federation",
    "fundamentos notebooks jobs lakeflow": "Developing Code for Data Processing using Python and SQL",
    "governanca catalogo e metadados": "Data Governance",
    "jobs alertas e spark ui": "Monitoring and Alerting",
    "medallion modelagem e dimensoes": "Data Modelling",
    "seguranca views e secrets": "Ensuring Data Security and Compliance",
    "structured streaming": "Data Transformation, Cleansing and Quality",
    "troubleshooting e performance": "Debugging and Deploying",
    "adicao": "Adição",
    "aritmetica": "Aritmética",
    "divisao": "Divisão",
    "fracao": "Fração",
    "fracoes": "Frações",
    "multiplicacao": "Multiplicação",
    "porcentagem": "Porcentagem",
    "radiciacao": "Radiciação",
    "subtracao": "Subtração",
}
LOWERCASE_LABEL_WORDS = {"a", "as", "com", "da", "das", "de", "do", "dos", "e", "em", "o", "os", "para", "por"}
UPPERCASE_LABEL_WORDS = {"api", "bi", "cdc", "ci", "cli", "dbfs", "dlt", "etl", "ia", "sql", "ui"}


@dataclass(frozen=True, slots=True)
class QuestionRowIssue:
    """Validation issue tied to one canonical question-bank row."""

    row_index: int
    row_number: int
    message: str


@dataclass(frozen=True, slots=True)
class SubjectTopicGroup:
    """One subject plus the active topics available under it."""

    subject: str
    topics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuestionFilterSelection:
    """Multi-select learner filter state across subjects and specific topics."""

    subjects: tuple[str, ...] = ()
    topics: tuple[tuple[str, str], ...] = ()


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
    for index, row in iter_dataframe_rows(prepared):
        row_number = worksheet_row_number(index)
        try:
            question = _parse_question_row(row)
        except ValueError as exc:
            issues.append(f"{QUESTION_RESOURCE_NAME} row {row_number}: {exc}")
            continue
        if question is not None:
            questions.append(question)
    return questions, issues


def parse_question_id_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[int], list[str]]:
    """Parse a dataframe containing only active question identifiers."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, ["id_question"], QUESTION_RESOURCE_NAME)
    ensure_unique_integer_values(prepared, "id_question", QUESTION_RESOURCE_NAME)

    question_ids: list[int] = []
    issues: list[str] = []
    for index, row in iter_dataframe_rows(prepared):
        row_number = worksheet_row_number(index)
        try:
            question_ids.append(_parse_required_int(row.get("id_question"), "id_question"))
        except ValueError as exc:
            issues.append(f"{QUESTION_RESOURCE_NAME} row {row_number}: {exc}")
    return question_ids, issues


def parse_question_index_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[QuestionIndexEntry], list[str]]:
    """Parse a lightweight dataframe used for subject filtering and selection."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, ["id_question"], QUESTION_RESOURCE_NAME)
    ensure_unique_integer_values(prepared, "id_question", QUESTION_RESOURCE_NAME)

    entries: list[QuestionIndexEntry] = []
    issues: list[str] = []
    for index, row in iter_dataframe_rows(prepared):
        row_number = worksheet_row_number(index)
        try:
            entries.append(
                QuestionIndexEntry(
                    id_question=_parse_required_int(row.get("id_question"), "id_question"),
                    subject=normalize_taxonomy_value(row.get("subject")),
                    topic=normalize_taxonomy_value(row.get("topic")),
                    cohort_key=_parse_optional_cohort_key(row.get("cohort_key")),
                )
            )
        except ValueError as exc:
            issues.append(f"{QUESTION_RESOURCE_NAME} row {row_number}: {exc}")
    return entries, issues


def parse_project_options_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Parse one distinct-project dataframe for teacher filtering."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(prepared, ["cohort_key"], QUESTION_RESOURCE_NAME)

    project_options: list[str] = []
    seen_projects: set[str] = set()
    issues: list[str] = []
    for index, row in iter_dataframe_rows(prepared):
        row_number = worksheet_row_number(index)
        try:
            project = _parse_optional_cohort_key(row.get("cohort_key"))
            if project is None or project in seen_projects:
                continue
            seen_projects.add(project)
            project_options.append(project)
        except ValueError as exc:
            issues.append(f"{QUESTION_RESOURCE_NAME} row {row_number}: {exc}")
    return sorted(project_options, key=str.casefold), issues


def parse_single_question_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[Question | None, list[str]]:
    """Parse a dataframe expected to contain at most one active question row."""

    questions, issues = parse_question_bank_dataframe(dataframe)
    if len(questions) > 1:
        issues.append("question_bank query returned more than one row for a single question lookup.")
    if not questions:
        return None, issues
    return questions[0], issues


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
    for index, row in iter_dataframe_rows(prepared):
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
            _parse_question_row(row)
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


def select_next_question_id(
    question_ids: Iterable[int],
    answered_question_ids: set[int],
    *,
    randomizer: random.Random | None = None,
) -> int | None:
    """Select the next question ID, prioritizing unseen IDs first."""

    available_question_ids = sorted({int(question_id) for question_id in question_ids})
    if not available_question_ids:
        return None

    unseen_question_ids = [
        question_id
        for question_id in available_question_ids
        if question_id not in answered_question_ids
    ]
    pool = unseen_question_ids or available_question_ids
    chooser = randomizer or random.Random()
    return chooser.choice(pool)


def select_question_batch_ids(
    question_ids: Iterable[int],
    excluded_question_ids: set[int],
    *,
    limit: int,
    randomizer: random.Random | None = None,
) -> list[int]:
    """Select a randomized batch of question IDs that are still eligible for prefetch."""

    if limit <= 0:
        return []

    available_question_ids = [
        question_id
        for question_id in sorted({int(question_id) for question_id in question_ids})
        if question_id not in excluded_question_ids
    ]
    if not available_question_ids:
        return []

    chooser = randomizer or random.Random()
    if len(available_question_ids) <= limit:
        chooser.shuffle(available_question_ids)
        return available_question_ids
    return chooser.sample(available_question_ids, k=limit)


def build_subject_options(question_index: Sequence[QuestionIndexEntry]) -> list[str]:
    """Build sorted subject filter options for the practice screen."""

    subjects = sorted(
        {
            subject
            for entry in question_index
            for subject in [normalize_taxonomy_value(entry.subject)]
            if subject
        },
        key=str.casefold,
    )
    return ["Tudo", *subjects]


def build_subject_topic_groups(
    question_index: Sequence[QuestionIndexEntry],
) -> list[SubjectTopicGroup]:
    """Build sorted subject/topic groups for hierarchical filtering in the learner UI."""

    topics_by_subject: dict[str, set[str]] = {}
    for entry in question_index:
        subject = normalize_taxonomy_value(entry.subject)
        if not subject:
            continue
        topics_by_subject.setdefault(subject, set())
        topic = normalize_taxonomy_value(entry.topic)
        if topic:
            topics_by_subject[subject].add(topic)

    return [
        SubjectTopicGroup(
            subject=subject,
            topics=tuple(sorted(topics, key=str.casefold)),
        )
        for subject, topics in sorted(topics_by_subject.items(), key=lambda item: item[0].casefold())
    ]


def build_project_options(question_index: Sequence[QuestionIndexEntry]) -> list[str]:
    """Build sorted project filter options for teacher users."""

    return sorted(
        {
            cohort_key
            for entry in question_index
            for cohort_key in [entry.cohort_key]
            if cohort_key
        },
        key=str.casefold,
    )


def filter_question_index_by_project(
    question_index: Sequence[QuestionIndexEntry],
    project: str | None,
) -> list[QuestionIndexEntry]:
    """Return the active question index filtered by one project/cohort."""

    selected_project = _normalize_project_key(project)
    return [
        entry
        for entry in question_index
        if selected_project is None or entry.cohort_key == selected_project
    ]


def filter_question_ids_by_subject(
    question_index: Sequence[QuestionIndexEntry],
    subject: str | None,
    *,
    topic: str | None = None,
) -> list[int]:
    """Return active question IDs for the selected subject/topic filter."""

    selected_subject = normalize_taxonomy_value(subject)
    selected_topic = normalize_taxonomy_value(topic)
    return [
        entry.id_question
        for entry in question_index
        if (
            selected_subject is None
            or normalize_taxonomy_value(entry.subject) == selected_subject
        )
        and (
            selected_topic is None
            or normalize_taxonomy_value(entry.topic) == selected_topic
        )
    ]


def filter_question_ids_by_filters(
    question_index: Sequence[QuestionIndexEntry],
    filters: QuestionFilterSelection,
) -> list[int]:
    """Return active question IDs for the selected multi-filter state."""

    if not filters.subjects and not filters.topics:
        return [entry.id_question for entry in question_index]

    selected_subjects = set(filters.subjects)
    selected_topics = set(filters.topics)
    matching_question_ids: list[int] = []
    for entry in question_index:
        subject = normalize_taxonomy_value(entry.subject)
        topic = normalize_taxonomy_value(entry.topic)
        matches_subject = not selected_subjects or subject in selected_subjects
        matches_topic = not selected_topics or (
            subject is not None
            and topic is not None
            and (subject, topic) in selected_topics
        )
        if matches_subject and matches_topic:
            matching_question_ids.append(entry.id_question)
    return matching_question_ids


def normalize_question_filters(
    question_index: Sequence[QuestionIndexEntry],
    *,
    subject: str | None,
    topic: str | None,
) -> tuple[str | None, str | None]:
    """Normalize one subject/topic filter pair against the active question index."""

    selected_subject = normalize_taxonomy_value(subject)
    selected_topic = normalize_taxonomy_value(topic)
    subject_groups = build_subject_topic_groups(question_index)
    available_subjects = {group.subject for group in subject_groups}
    if selected_subject not in available_subjects:
        return None, None

    available_topics = {
        topic_name
        for group in subject_groups
        if group.subject == selected_subject
        for topic_name in group.topics
    }
    if selected_topic not in available_topics:
        return selected_subject, None
    return selected_subject, selected_topic


def normalize_multi_question_filters(
    question_index: Sequence[QuestionIndexEntry],
    *,
    subjects: Sequence[str] | None,
    topics: Sequence[tuple[str, str]] | None,
) -> QuestionFilterSelection:
    """Normalize one multi-select filter state against the active question index."""

    subject_groups = build_subject_topic_groups(question_index)
    available_topics_by_subject = {
        group.subject: set(group.topics)
        for group in subject_groups
    }

    normalized_subjects = tuple(
        sorted(
            {
                normalized_subject
                for subject in (subjects or [])
                for normalized_subject in [normalize_taxonomy_value(subject)]
                if normalized_subject in available_topics_by_subject
            },
            key=str.casefold,
        )
    )
    selected_subject_set = set(normalized_subjects)

    normalized_topics = tuple(
        sorted(
            {
                (normalized_subject, normalized_topic)
                for raw_topic in (topics or [])
                if len(raw_topic) == 2
                for normalized_subject in [normalize_taxonomy_value(raw_topic[0])]
                for normalized_topic in [normalize_taxonomy_value(raw_topic[1])]
                if normalized_subject in available_topics_by_subject
                and (
                    not selected_subject_set
                    or normalized_subject in selected_subject_set
                )
                and normalized_topic in available_topics_by_subject[normalized_subject]
            },
            key=lambda item: (item[0].casefold(), item[1].casefold()),
        )
    )

    return QuestionFilterSelection(
        subjects=normalized_subjects,
        topics=normalized_topics,
    )


def format_project_label(project: str | None) -> str:
    """Render one cohort/project key as a readable Portuguese-BR label."""

    normalized_project = _normalize_project_key(project)
    if normalized_project is None:
        return ""

    explicit_label = PROJECT_LABEL_BY_KEY.get(normalized_project)
    if explicit_label is not None:
        return explicit_label

    words = normalized_project.replace("_", " ").split()
    if not words:
        return normalized_project

    lower_words = {"e", "de", "da", "do", "das", "dos"}
    formatted_words: list[str] = []
    for index, word in enumerate(words):
        if index > 0 and word in lower_words:
            formatted_words.append(word)
        else:
            formatted_words.append(word.capitalize())
    return " ".join(formatted_words)


def format_subject_label(subject: str | None) -> str:
    """Render one subject key as a readable Portuguese-BR label."""

    normalized_subject = normalize_taxonomy_value(subject)
    if not normalized_subject:
        return ""

    explicit_label = SUBJECT_LABEL_BY_KEY.get(normalized_subject)
    if explicit_label is not None:
        return explicit_label
    return _format_canonical_label(normalized_subject)


def format_topic_label(topic: str | None) -> str:
    """Render one topic key as a readable Portuguese-BR label."""

    normalized_topic = normalize_taxonomy_value(topic)
    if not normalized_topic:
        return ""

    explicit_label = TOPIC_LABEL_BY_KEY.get(normalized_topic)
    if explicit_label is not None:
        return explicit_label
    return _format_canonical_label(normalized_topic)


def format_subject_topic_filter_label(
    subject: str | None,
    topic: str | None,
) -> str:
    """Render the current hierarchical learner filter as one compact label."""

    normalized_subject = normalize_taxonomy_value(subject)
    normalized_topic = normalize_taxonomy_value(topic)
    if not normalized_subject:
        return "Tudo"
    if not normalized_topic:
        return format_subject_label(normalized_subject)
    return f"{format_subject_label(normalized_subject)} · {format_topic_label(normalized_topic)}"


def format_question_filter_label(filters: QuestionFilterSelection) -> str:
    """Render one compact label for the current multi-select learner filter."""

    selection_count = len(filters.subjects) + len(filters.topics)
    if selection_count == 0:
        return "Tudo"
    if len(filters.subjects) == 1 and not filters.topics:
        return format_subject_label(filters.subjects[0])
    if len(filters.topics) == 1 and not filters.subjects:
        subject, topic = filters.topics[0]
        return f"{format_subject_label(subject)} / {format_topic_label(topic)}"
    if len(filters.subjects) == 1 and len(filters.topics) == 1:
        subject = filters.subjects[0]
        topic_subject, topic = filters.topics[0]
        if subject == topic_subject:
            return f"{format_subject_label(subject)} / {format_topic_label(topic)}"
    return f"{selection_count} filtros"


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
        subject=normalize_taxonomy_value(row.get("subject")),
        topic=normalize_taxonomy_value(row.get("topic")),
        difficulty=clean_optional_text(row.get("difficulty")),
        source=clean_optional_text(row.get("source")),
        cohort_key=_parse_optional_cohort_key(row.get("cohort_key")),
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


def _parse_optional_cohort_key(value: object) -> str | None:
    cohort_key = clean_optional_text(value)
    if not cohort_key:
        return None
    return cohort_key.lower()


def _normalize_project_key(value: object) -> str | None:
    project = clean_optional_text(value)
    if not project:
        return None
    return project.lower()


def _format_canonical_label(value: str) -> str:
    words = value.split()
    formatted_words: list[str] = []
    for index, word in enumerate(words):
        if word in UPPERCASE_LABEL_WORDS:
            formatted_words.append(word.upper())
        elif index > 0 and word in LOWERCASE_LABEL_WORDS:
            formatted_words.append(word)
        else:
            formatted_words.append(word.capitalize())
    return " ".join(formatted_words)


def _find_duplicate_id_by_index(dataframe: pd.DataFrame) -> dict[int, int]:
    ids_by_index: dict[int, int] = {}
    row_indexes_by_id: dict[int, list[int]] = {}

    for index, row in iter_dataframe_rows(dataframe):
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
