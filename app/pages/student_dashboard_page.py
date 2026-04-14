from __future__ import annotations

from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from app.ui.question_session import format_elapsed_time
from modules.domain.models import StudentDashboardSummary, StudentSubjectPerformance, User
from modules.services.question_service import format_topic_label


def render_student_dashboard_page(
    *,
    user: User,
    selected_project: str | None,
    summary: StudentDashboardSummary,
    subject_performance: list[StudentSubjectPerformance],
) -> None:
    """Render a lightweight learner dashboard for the current project scope."""

    del selected_project

    _apply_student_dashboard_styles()
    st.html(_build_dashboard_header_html(user=user))

    metric_columns = st.columns(3, gap="small")

    with metric_columns[0]:
        st.html(
            _build_metric_card_html(
                title="Acertos",
                value=str(summary.total_correct),
                detail=_format_percent(_share(summary.total_correct, summary.total_answers)),
                tone="success",
            )
        )
    with metric_columns[1]:
        st.html(
            _build_metric_card_html(
                title="Erros",
                value=str(summary.total_wrong),
                detail=_format_percent(_share(summary.total_wrong, summary.total_answers)),
                tone="danger",
            )
        )
    with metric_columns[2]:
        st.html(
            _build_metric_card_html(
                title="Tempo m\u00e9dio",
                value=_format_duration(summary.average_time_spent_seconds),
                detail=(
                    "Certas "
                    f"{_format_duration(summary.average_correct_time_spent_seconds)} "
                    "\u00b7 Erradas "
                    f"{_format_duration(summary.average_wrong_time_spent_seconds)}"
                ),
                tone="neutral",
            )
        )

    if summary.total_answers <= 0 or not subject_performance:
        st.html(
            _build_empty_state_html(
                "Ainda n\u00e3o h\u00e1 respostas suficientes para montar o gr\u00e1fico por t\u00f3pico neste projeto."
            )
        )
        return

    st.html(_build_section_header_html(title="Desempenho por t\u00f3pico"))
    st.altair_chart(
        _build_subject_performance_chart(subject_performance),
        use_container_width=True,
    )


def _apply_student_dashboard_styles() -> None:
    st.html(
        """
        <style>
        .gm-stats-hero,
        .gm-stats-card,
        .gm-stats-empty,
        .gm-stats-section {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid #dbeafe;
            border-radius: 1.15rem;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
        }

        .gm-stats-hero {
            margin: 0 auto 0.65rem;
            max-width: calc(100% - 1.1rem);
            padding: 0.95rem 1.05rem 0.9rem;
        }

        .gm-stats-eyebrow {
            color: #475569;
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .gm-stats-title {
            color: #0f172a;
            font-size: 1.18rem;
            font-weight: 800;
            line-height: 1.2;
            margin: 0;
        }

        .gm-stats-card {
            height: 100%;
            margin: 0 auto;
            max-width: calc(100% - 1.1rem);
            padding: 0.95rem 1rem 0.9rem;
        }

        .gm-stats-card-label {
            color: #64748b;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .gm-stats-card-value {
            color: #0f172a;
            font-size: 1.65rem;
            font-weight: 800;
            line-height: 1.1;
            margin: 0;
        }

        .gm-stats-card-detail {
            border-top: 1px solid rgba(148, 163, 184, 0.2);
            color: #64748b;
            font-size: 0.84rem;
            line-height: 1.4;
            margin-top: 0.52rem;
            padding-top: 0.48rem;
        }

        .gm-stats-card--success {
            border-color: #bbf7d0;
        }

        .gm-stats-card--success .gm-stats-card-value {
            color: #15803d;
        }

        .gm-stats-card--danger {
            border-color: #fecaca;
        }

        .gm-stats-card--danger .gm-stats-card-value {
            color: #b91c1c;
        }

        .gm-stats-card--neutral .gm-stats-card-value {
            color: #0f172a;
        }

        .gm-stats-empty,
        .gm-stats-section {
            margin: 0.7rem auto 0;
            max-width: calc(100% - 1.1rem);
            padding: 0.88rem 1rem;
        }

        .gm-stats-section-title {
            color: #0f172a;
            font-size: 0.98rem;
            font-weight: 800;
            line-height: 1.2;
            margin: 0;
        }

        .gm-stats-empty-text {
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.45;
            margin-top: 0.38rem;
        }

        div[data-testid="stVegaLiteChart"] {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid #dbeafe;
            border-radius: 1.15rem;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
            margin: 0 auto;
            max-width: calc(100% - 1.1rem);
            padding: 0.65rem 0.7rem 0.25rem;
        }
        </style>
        """
    )


def _build_dashboard_header_html(
    *,
    user: User,
) -> str:
    learner_label = escape(user.display_name)
    return (
        '<section class="gm-stats-hero">'
        '<div class="gm-stats-eyebrow">Dashboard do aluno</div>'
        f'<h1 class="gm-stats-title">Seu desempenho, {learner_label}</h1>'
        "</section>"
    )


def _build_metric_card_html(*, title: str, value: str, detail: str, tone: str) -> str:
    return (
        f'<section class="gm-stats-card gm-stats-card--{escape(tone)}">'
        f'<div class="gm-stats-card-label">{escape(title)}</div>'
        f'<div class="gm-stats-card-value">{escape(value)}</div>'
        f'<div class="gm-stats-card-detail">{escape(detail)}</div>'
        "</section>"
    )


def _build_section_header_html(*, title: str) -> str:
    return (
        '<section class="gm-stats-section">'
        f'<div class="gm-stats-section-title">{escape(title)}</div>'
        "</section>"
    )


def _build_empty_state_html(message: str) -> str:
    return (
        '<section class="gm-stats-empty">'
        '<div class="gm-stats-section-title">Gr\u00e1fico indispon\u00edvel por enquanto</div>'
        f'<div class="gm-stats-empty-text">{escape(message)}</div>'
        "</section>"
    )


def _build_subject_performance_chart(
    subject_performance: list[StudentSubjectPerformance],
) -> alt.LayerChart:
    chart_data = pd.DataFrame(
        [
            {
                "topic_label": _format_subject_stat_label(item.subject),
                "accuracy_percent": round(item.accuracy_rate * 100, 1),
                "total_answers": item.total_answers,
                "total_correct": item.total_correct,
                "total_wrong": item.total_wrong,
                "average_time_label": _format_duration(item.average_time_spent_seconds),
            }
            for item in subject_performance
        ]
    )
    topic_order = chart_data["topic_label"].tolist()

    base = alt.Chart(chart_data).encode(
        x=alt.X(
            "topic_label:N",
            sort=topic_order,
            axis=alt.Axis(title="T\u00f3picos", labelAngle=-18, labelLimit=220),
        )
    )
    tooltip = [
        alt.Tooltip("topic_label:N", title="T\u00f3pico"),
        alt.Tooltip("accuracy_percent:Q", title="% de acerto", format=".1f"),
        alt.Tooltip("total_correct:Q", title="Acertos"),
        alt.Tooltip("total_wrong:Q", title="Erros"),
        alt.Tooltip("total_answers:Q", title="Respostas"),
        alt.Tooltip("average_time_label:N", title="Tempo m\u00e9dio"),
    ]

    bars = base.mark_bar(
        color="#bfdbfe",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8,
        opacity=0.95,
        size=34,
    ).encode(
        y=alt.Y(
            "accuracy_percent:Q",
            axis=alt.Axis(title="% de acerto", format=".0f"),
            scale=alt.Scale(domain=[0, 100]),
        ),
        tooltip=tooltip,
    )

    line = base.mark_line(
        color="#1d4ed8",
        point=alt.OverlayMarkDef(fill="#1d4ed8", filled=True, size=78),
        strokeWidth=3,
    ).encode(
        y=alt.Y(
            "total_correct:Q",
            axis=alt.Axis(title="Qtd. de acertos", orient="right"),
        ),
        tooltip=tooltip,
    )

    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(height=320)
        .configure_view(strokeOpacity=0)
    )


def _format_subject_stat_label(subject: str | None) -> str:
    formatted_subject = format_topic_label(subject)
    if formatted_subject:
        return formatted_subject
    return "Sem t\u00f3pico"


def _share(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(min(part / total, 1.0), 0.0)


def _format_percent(value: float) -> str:
    return f"{max(min(value, 1.0), 0.0) * 100:.1f}%"


def _format_duration(seconds: float) -> str:
    return format_elapsed_time(int(round(max(seconds or 0.0, 0.0))))
