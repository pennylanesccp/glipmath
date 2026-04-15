from __future__ import annotations

from app.pages import student_dashboard_page
from modules.domain.models import StudentSubjectPerformance, User


def test_build_dashboard_header_html_keeps_only_the_student_title() -> None:
    html = student_dashboard_page._build_dashboard_header_html(
        user=User(email="ana@example.com", name="Ana"),
    )

    assert "Seu desempenho, Ana" in html
    assert "Projeto:" not in html
    assert "Respostas:" not in html
    assert "Resumo" not in html


def test_build_metric_card_html_renders_divider_detail_section() -> None:
    html = student_dashboard_page._build_metric_card_html(
        title="Acertos",
        value="3",
        detail="75.0%",
        tone="success",
    )

    assert "gm-stats-card-detail" in html
    assert "75.0%" in html


def test_build_subject_performance_chart_uses_topic_labels_on_the_x_axis() -> None:
    chart = student_dashboard_page._build_subject_performance_chart(
        [
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
    )

    spec = chart.to_dict()

    assert spec["resolve"]["scale"]["y"] == "independent"
    assert len(spec["layer"]) == 2
    assert spec["layer"][0]["encoding"]["x"]["axis"]["title"] == "Tópicos"
    assert spec["layer"][0]["encoding"]["x"]["field"] == "topic_axis_label"
    assert spec["layer"][0]["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert spec["layer"][0]["encoding"]["x"]["axis"]["labelOverlap"] is False
    dataset = next(iter(spec["datasets"].values()))
    assert dataset[0]["topic_label"] == "Data Transformation, Cleansing and Quality"
    assert dataset[0]["topic_axis_label"] == "Data Transformation,\nCleansing and\nQuality"
    assert dataset[1]["topic_label"] == "Sem tópico"
    assert dataset[1]["topic_axis_label"] == "Sem tópico"


def test_wrap_chart_axis_label_breaks_long_topic_names() -> None:
    assert (
        student_dashboard_page._wrap_chart_axis_label("Data Ingestion & Acquisition")
        == "Data Ingestion &\nAcquisition"
    )
    assert student_dashboard_page._wrap_chart_axis_label("Sem tópico") == "Sem tópico"
