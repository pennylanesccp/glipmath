from __future__ import annotations

import math

import pandas as pd

from modules.domain.models import (
    StudentDashboardSummary,
    StudentSubjectPerformance,
    StudentTopicProgress,
)
from modules.storage.schema_validation import (
    iter_dataframe_rows,
    prepare_dataframe,
    require_columns,
    worksheet_row_number,
)
from modules.utils.normalization import clean_optional_text, normalize_taxonomy_value

STUDENT_DASHBOARD_SUMMARY_RESOURCE_NAME = "student_dashboard_summary"
STUDENT_SUBJECT_PERFORMANCE_RESOURCE_NAME = "student_subject_performance"
STUDENT_TOPIC_PROGRESS_RESOURCE_NAME = "student_topic_progress"


def parse_student_dashboard_summary_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[StudentDashboardSummary, list[str]]:
    """Parse one-row learner summary aggregates from BigQuery."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return StudentDashboardSummary(), []

    require_columns(
        prepared,
        [
            "total_answers",
            "total_correct",
            "total_wrong",
            "accuracy_rate",
            "average_time_spent_seconds",
            "average_correct_time_spent_seconds",
            "average_wrong_time_spent_seconds",
        ],
        STUDENT_DASHBOARD_SUMMARY_RESOURCE_NAME,
    )

    issues: list[str] = []
    if len(prepared.index) > 1:
        issues.append(
            "student_dashboard_summary query returned more than one row for a single learner summary."
        )

    row = prepared.iloc[0]
    try:
        summary = StudentDashboardSummary(
            total_answers=_parse_non_negative_int(row.get("total_answers"), "total_answers"),
            total_correct=_parse_non_negative_int(row.get("total_correct"), "total_correct"),
            total_wrong=_parse_non_negative_int(row.get("total_wrong"), "total_wrong"),
            accuracy_rate=_parse_ratio(row.get("accuracy_rate"), "accuracy_rate"),
            average_time_spent_seconds=_parse_non_negative_float(
                row.get("average_time_spent_seconds"),
                "average_time_spent_seconds",
            ),
            average_correct_time_spent_seconds=_parse_non_negative_float(
                row.get("average_correct_time_spent_seconds"),
                "average_correct_time_spent_seconds",
            ),
            average_wrong_time_spent_seconds=_parse_non_negative_float(
                row.get("average_wrong_time_spent_seconds"),
                "average_wrong_time_spent_seconds",
            ),
        )
    except ValueError as exc:
        issues.append(
            f"{STUDENT_DASHBOARD_SUMMARY_RESOURCE_NAME} row "
            f"{worksheet_row_number(prepared.index[0])}: {exc}"
        )
        summary = StudentDashboardSummary()
    return summary, issues


def parse_student_subject_performance_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[StudentSubjectPerformance], list[str]]:
    """Parse per-subject learner aggregates from BigQuery."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    topic_column = "topic" if "topic" in prepared.columns else "subject"
    require_columns(
        prepared,
        [
            topic_column,
            "total_answers",
            "total_correct",
            "total_wrong",
            "accuracy_rate",
            "average_time_spent_seconds",
        ],
        STUDENT_SUBJECT_PERFORMANCE_RESOURCE_NAME,
    )

    subject_performance: list[StudentSubjectPerformance] = []
    issues: list[str] = []
    for index, row in iter_dataframe_rows(prepared):
        try:
            subject_performance.append(
                StudentSubjectPerformance(
                    subject=normalize_taxonomy_value(row.get(topic_column)),
                    total_answers=_parse_non_negative_int(row.get("total_answers"), "total_answers"),
                    total_correct=_parse_non_negative_int(row.get("total_correct"), "total_correct"),
                    total_wrong=_parse_non_negative_int(row.get("total_wrong"), "total_wrong"),
                    accuracy_rate=_parse_ratio(row.get("accuracy_rate"), "accuracy_rate"),
                    average_time_spent_seconds=_parse_non_negative_float(
                        row.get("average_time_spent_seconds"),
                        "average_time_spent_seconds",
                    ),
                )
            )
        except ValueError as exc:
            issues.append(
                f"{STUDENT_SUBJECT_PERFORMANCE_RESOURCE_NAME} row "
                f"{worksheet_row_number(index)}: {exc}"
            )

    return subject_performance, issues


def parse_student_topic_progress_dataframe(
    dataframe: pd.DataFrame,
) -> tuple[list[StudentTopicProgress], list[str]]:
    """Parse active-question completion and answer-attempt metrics by topic."""

    prepared = prepare_dataframe(dataframe)
    if prepared.empty and not list(prepared.columns):
        return [], []

    require_columns(
        prepared,
        [
            "subject",
            "topic",
            "total_questions",
            "answered_questions",
            "remaining_questions",
            "completion_rate",
            "total_answers",
            "total_correct",
            "total_wrong",
            "accuracy_rate",
            "average_time_spent_seconds",
        ],
        STUDENT_TOPIC_PROGRESS_RESOURCE_NAME,
    )

    topic_progress: list[StudentTopicProgress] = []
    issues: list[str] = []
    for index, row in iter_dataframe_rows(prepared):
        try:
            topic_progress.append(
                StudentTopicProgress(
                    subject=normalize_taxonomy_value(row.get("subject")),
                    topic=normalize_taxonomy_value(row.get("topic")),
                    total_questions=_parse_non_negative_int(
                        row.get("total_questions"),
                        "total_questions",
                    ),
                    answered_questions=_parse_non_negative_int(
                        row.get("answered_questions"),
                        "answered_questions",
                    ),
                    remaining_questions=_parse_non_negative_int(
                        row.get("remaining_questions"),
                        "remaining_questions",
                    ),
                    completion_rate=_parse_ratio(
                        row.get("completion_rate"),
                        "completion_rate",
                    ),
                    total_answers=_parse_non_negative_int(
                        row.get("total_answers"),
                        "total_answers",
                    ),
                    total_correct=_parse_non_negative_int(
                        row.get("total_correct"),
                        "total_correct",
                    ),
                    total_wrong=_parse_non_negative_int(
                        row.get("total_wrong"),
                        "total_wrong",
                    ),
                    accuracy_rate=_parse_ratio(
                        row.get("accuracy_rate"),
                        "accuracy_rate",
                    ),
                    average_time_spent_seconds=_parse_non_negative_float(
                        row.get("average_time_spent_seconds"),
                        "average_time_spent_seconds",
                    ),
                )
            )
        except ValueError as exc:
            issues.append(
                f"{STUDENT_TOPIC_PROGRESS_RESOURCE_NAME} row "
                f"{worksheet_row_number(index)}: {exc}"
            )

    return topic_progress, issues


def _parse_non_negative_int(value: object, field_name: str) -> int:
    text = clean_optional_text(value)
    if text is None:
        return 0
    try:
        parsed = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid integer.") from exc
    if not math.isfinite(parsed) or not parsed.is_integer():
        raise ValueError(f"{field_name} must be a valid integer.")
    return max(int(parsed), 0)


def _parse_non_negative_float(value: object, field_name: str) -> float:
    text = clean_optional_text(value)
    if text is None:
        return 0.0
    try:
        parsed = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid number.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite.")
    return max(parsed, 0.0)


def _parse_ratio(value: object, field_name: str) -> float:
    parsed = _parse_non_negative_float(value, field_name)
    return min(parsed, 1.0)
