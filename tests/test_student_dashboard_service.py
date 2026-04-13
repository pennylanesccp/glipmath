from __future__ import annotations

import pandas as pd

from modules.domain.models import StudentDashboardSummary, StudentSubjectPerformance
from modules.services.student_dashboard_service import (
    parse_student_dashboard_summary_dataframe,
    parse_student_subject_performance_dataframe,
)


def test_parse_student_dashboard_summary_dataframe_reads_aggregate_metrics() -> None:
    summary, issues = parse_student_dashboard_summary_dataframe(
        pd.DataFrame(
            [
                {
                    "total_answers": 20,
                    "total_correct": 14,
                    "total_wrong": 6,
                    "accuracy_rate": 0.7,
                    "average_time_spent_seconds": 41.5,
                    "average_correct_time_spent_seconds": 35.2,
                    "average_wrong_time_spent_seconds": 56.8,
                }
            ]
        )
    )

    assert issues == []
    assert summary == StudentDashboardSummary(
        total_answers=20,
        total_correct=14,
        total_wrong=6,
        accuracy_rate=0.7,
        average_time_spent_seconds=41.5,
        average_correct_time_spent_seconds=35.2,
        average_wrong_time_spent_seconds=56.8,
    )


def test_parse_student_dashboard_summary_dataframe_defaults_blank_numeric_values_to_zero() -> None:
    summary, issues = parse_student_dashboard_summary_dataframe(
        pd.DataFrame(
            [
                {
                    "total_answers": "",
                    "total_correct": "",
                    "total_wrong": "",
                    "accuracy_rate": "",
                    "average_time_spent_seconds": "",
                    "average_correct_time_spent_seconds": "",
                    "average_wrong_time_spent_seconds": "",
                }
            ]
        )
    )

    assert issues == []
    assert summary == StudentDashboardSummary()


def test_parse_student_subject_performance_dataframe_reads_rows_and_normalizes_subjects() -> None:
    subject_performance, issues = parse_student_subject_performance_dataframe(
        pd.DataFrame(
            [
                {
                    "subject": "Matemática",
                    "total_answers": 12,
                    "total_correct": 9,
                    "total_wrong": 3,
                    "accuracy_rate": 0.75,
                    "average_time_spent_seconds": 38.2,
                },
                {
                    "subject": "",
                    "total_answers": 5,
                    "total_correct": 2,
                    "total_wrong": 3,
                    "accuracy_rate": 0.4,
                    "average_time_spent_seconds": 52.0,
                },
            ]
        )
    )

    assert issues == []
    assert subject_performance == [
        StudentSubjectPerformance(
            subject="matematica",
            total_answers=12,
            total_correct=9,
            total_wrong=3,
            accuracy_rate=0.75,
            average_time_spent_seconds=38.2,
        ),
        StudentSubjectPerformance(
            subject=None,
            total_answers=5,
            total_correct=2,
            total_wrong=3,
            accuracy_rate=0.4,
            average_time_spent_seconds=52.0,
        ),
    ]
