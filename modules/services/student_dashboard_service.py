from __future__ import annotations

import math

import pandas as pd

from modules.domain.models import StudentDashboardSummary, StudentSubjectPerformance
from modules.storage.schema_validation import (
    iter_dataframe_rows,
    prepare_dataframe,
    require_columns,
    worksheet_row_number,
)
from modules.utils.normalization import clean_optional_text, normalize_taxonomy_value

STUDENT_DASHBOARD_SUMMARY_RESOURCE_NAME = "student_dashboard_summary"
STUDENT_SUBJECT_PERFORMANCE_RESOURCE_NAME = "student_subject_performance"


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

    require_columns(
        prepared,
        [
            "subject",
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
                    subject=normalize_taxonomy_value(row.get("subject")),
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
    if parsed > 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")
    return parsed
