from __future__ import annotations

from app.pages import student_dashboard_page
from modules.domain.models import StudentSubjectPerformance, StudentTopicProgress, User


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
        ],
        topic_progress=[
            StudentTopicProgress(
                subject="databricks",
                topic="structured streaming",
                total_questions=20,
                answered_questions=8,
                remaining_questions=12,
                completion_rate=0.4,
            )
        ],
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
    assert dataset[0]["completion_label"] == "40.0%"
    assert dataset[0]["answered_questions"] == 8
    assert dataset[0]["total_questions"] == 20
    assert dataset[0]["remaining_questions"] == 12
    assert dataset[1]["topic_label"] == "Sem tópico"
    assert dataset[1]["topic_axis_label"] == "Sem tópico"


def test_wrap_chart_axis_label_breaks_long_topic_names() -> None:
    assert (
        student_dashboard_page._wrap_chart_axis_label("Data Ingestion & Acquisition")
        == "Data Ingestion &\nAcquisition"
    )
    assert student_dashboard_page._wrap_chart_axis_label("Sem tópico") == "Sem tópico"


def test_progress_cards_and_map_render_completion_counts_and_statuses() -> None:
    topic_progress = [
        StudentTopicProgress(
            subject="gestao de recursos hidricos",
            topic="tratamento de agua",
            total_questions=10,
            answered_questions=0,
            remaining_questions=10,
            completion_rate=0.0,
        ),
        StudentTopicProgress(
            subject="gestao de recursos hidricos",
            topic="reuso",
            total_questions=10,
            answered_questions=3,
            remaining_questions=7,
            completion_rate=0.3,
            total_answers=4,
            total_correct=3,
            total_wrong=1,
            accuracy_rate=0.75,
        ),
        StudentTopicProgress(
            subject=None,
            topic=None,
            total_questions=4,
            answered_questions=2,
            remaining_questions=2,
            completion_rate=0.5,
        ),
        StudentTopicProgress(
            subject="matematica",
            topic="divisao",
            total_questions=2,
            answered_questions=2,
            remaining_questions=0,
            completion_rate=1.0,
        ),
    ]

    overview_html = student_dashboard_page._build_progress_overview_card_html(topic_progress)
    progress_html = student_dashboard_page._build_topic_progress_html(topic_progress)

    assert "7 / 26" in overview_html
    assert "19 faltando" in overview_html
    assert "Gestao de Recursos Hidricos" in progress_html
    assert "3/20 concluídas" in progress_html
    assert "3 / 10 resolvidas" in progress_html
    assert "7 faltando" in progress_html
    assert "Não iniciado" in progress_html
    assert "Começando" in progress_html
    assert "Em andamento" in progress_html
    assert "Concluído" in progress_html
    assert "Sem matéria" in progress_html
    assert "Sem tópico" in progress_html


def test_select_next_focus_prefers_remaining_count_then_lower_accuracy() -> None:
    high_accuracy = StudentTopicProgress(
        topic="tratamento de agua",
        total_questions=10,
        answered_questions=2,
        remaining_questions=8,
        completion_rate=0.2,
        accuracy_rate=0.8,
    )
    lower_accuracy = StudentTopicProgress(
        topic="reuso",
        total_questions=10,
        answered_questions=2,
        remaining_questions=8,
        completion_rate=0.2,
        accuracy_rate=0.4,
    )
    fewer_remaining = StudentTopicProgress(
        topic="captacao",
        total_questions=10,
        answered_questions=3,
        remaining_questions=7,
        completion_rate=0.3,
        accuracy_rate=0.1,
    )

    selected = student_dashboard_page._select_next_focus(
        [high_accuracy, fewer_remaining, lower_accuracy]
    )
    card_html = student_dashboard_page._build_next_focus_card_html(
        [high_accuracy, fewer_remaining, lower_accuracy]
    )

    assert selected == lower_accuracy
    assert "Próximo foco: Reuso" in card_html
    assert "8 perguntas faltando" in card_html
