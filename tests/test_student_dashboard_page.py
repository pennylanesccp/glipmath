from __future__ import annotations

from app.pages import student_dashboard_page
from modules.domain.models import StudentSubjectPerformance, User


def test_build_dashboard_header_html_includes_project_scope_and_total_answers() -> None:
    html = student_dashboard_page._build_dashboard_header_html(
        user=User(email="ana@example.com", name="Ana"),
        selected_project="ano_1",
        total_answers=24,
    )

    assert "Seu desempenho, Ana" in html
    assert "Projeto: Ano 1" in html
    assert "Respostas: 24" in html


def test_build_subject_performance_chart_uses_dual_axis_layers() -> None:
    chart = student_dashboard_page._build_subject_performance_chart(
        [
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
    )

    spec = chart.to_dict()

    assert spec["resolve"]["scale"]["y"] == "independent"
    assert len(spec["layer"]) == 2
    dataset = next(iter(spec["datasets"].values()))
    assert dataset[0]["subject_label"] == "Matemática"
    assert dataset[1]["subject_label"] == "Sem matéria"
