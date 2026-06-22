from __future__ import annotations

import pandas as pd

from modules.domain.models import (
    StudentDashboardSummary,
    StudentSubjectPerformance,
    StudentTopicProgress,
)
from modules.services.student_dashboard_service import (
    parse_student_dashboard_summary_dataframe,
    parse_student_subject_performance_dataframe,
    parse_student_topic_progress_dataframe,
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


def test_parse_student_subject_performance_dataframe_reads_rows_and_normalizes_topics() -> None:
    subject_performance, issues = parse_student_subject_performance_dataframe(
        pd.DataFrame(
            [
                {
                    "topic": "Structured Streaming",
                    "total_answers": 12,
                    "total_correct": 9,
                    "total_wrong": 3,
                    "accuracy_rate": 0.75,
                    "average_time_spent_seconds": 38.2,
                },
                {
                    "topic": "",
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
            subject="structured streaming",
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


def test_parse_student_topic_progress_dataframe_reads_progress_rows() -> None:
    topic_progress, issues = parse_student_topic_progress_dataframe(
        pd.DataFrame(
            [
                {
                    "subject": "Gestao de Recursos Hidricos",
                    "topic": "Tratamento de Agua",
                    "total_questions": 10,
                    "answered_questions": 4,
                    "remaining_questions": 6,
                    "completion_rate": 0.4,
                    "total_answers": 7,
                    "total_correct": 5,
                    "total_wrong": 2,
                    "accuracy_rate": 5 / 7,
                    "average_time_spent_seconds": 42.5,
                }
            ]
        )
    )

    assert issues == []
    assert topic_progress == [
        StudentTopicProgress(
            subject="gestao de recursos hidricos",
            topic="tratamento de agua",
            total_questions=10,
            answered_questions=4,
            remaining_questions=6,
            completion_rate=0.4,
            total_answers=7,
            total_correct=5,
            total_wrong=2,
            accuracy_rate=5 / 7,
            average_time_spent_seconds=42.5,
        )
    ]


def test_parse_student_topic_progress_dataframe_defaults_blank_values() -> None:
    topic_progress, issues = parse_student_topic_progress_dataframe(
        pd.DataFrame(
            [
                {
                    "subject": "",
                    "topic": None,
                    "total_questions": "",
                    "answered_questions": "",
                    "remaining_questions": "",
                    "completion_rate": "",
                    "total_answers": "",
                    "total_correct": "",
                    "total_wrong": "",
                    "accuracy_rate": "",
                    "average_time_spent_seconds": "",
                }
            ]
        )
    )

    assert issues == []
    assert topic_progress == [StudentTopicProgress()]


def test_parse_student_topic_progress_dataframe_clamps_ratios() -> None:
    topic_progress, issues = parse_student_topic_progress_dataframe(
        pd.DataFrame(
            [
                {
                    "subject": "matematica",
                    "topic": "divisao",
                    "total_questions": 2,
                    "answered_questions": 2,
                    "remaining_questions": 0,
                    "completion_rate": 1.4,
                    "total_answers": 2,
                    "total_correct": 0,
                    "total_wrong": 2,
                    "accuracy_rate": -0.3,
                    "average_time_spent_seconds": 10,
                }
            ]
        )
    )

    assert issues == []
    assert topic_progress[0].completion_rate == 1.0
    assert topic_progress[0].accuracy_rate == 0.0
