from __future__ import annotations

from html import escape
from textwrap import wrap

import altair as alt
import pandas as pd
import streamlit as st

from app.ui.question_session import format_elapsed_time
from modules.domain.models import (
    StudentDashboardSummary,
    StudentSubjectPerformance,
    StudentTopicProgress,
    User,
)
from modules.services.question_service import format_subject_label, format_topic_label
from modules.utils.normalization import normalize_taxonomy_value


def render_student_dashboard_page(
    *,
    user: User,
    selected_project: str | None,
    summary: StudentDashboardSummary,
    subject_performance: list[StudentSubjectPerformance],
    topic_progress: list[StudentTopicProgress],
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

    if not topic_progress:
        st.html(
            _build_empty_state_html(
                "Ainda n\u00e3o h\u00e1 perguntas ativas para este projeto.",
                title="Sem perguntas ativas",
            )
        )
        return

    st.html(_build_section_header_html(title="Progresso por mat\u00e9ria e t\u00f3pico"))
    progress_columns = st.columns(2, gap="small")
    with progress_columns[0]:
        st.html(_build_progress_overview_card_html(topic_progress))
    with progress_columns[1]:
        st.html(_build_next_focus_card_html(topic_progress))
    st.html(_build_topic_progress_html(topic_progress))

    if summary.total_answers <= 0 or not subject_performance:
        st.html(
            _build_empty_state_html(
                "Responda a primeira pergunta para liberar o gr\u00e1fico de acur\u00e1cia por t\u00f3pico."
            )
        )
        return

    st.html(_build_section_header_html(title="Desempenho por t\u00f3pico"))
    st.altair_chart(
        _build_subject_performance_chart(subject_performance, topic_progress=topic_progress),
        use_container_width=True,
    )


def _apply_student_dashboard_styles() -> None:
    st.html(
        """
        <style>
        .gm-stats-hero,
        .gm-stats-card,
        .gm-stats-empty,
        .gm-stats-section,
        .gm-progress-map {
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

        .gm-stats-card--progress {
            border-color: #bfdbfe;
        }

        .gm-stats-card--progress .gm-stats-card-value {
            color: #1d4ed8;
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

        .gm-progress-map {
            margin: 0.7rem auto 0;
            max-width: calc(100% - 1.1rem);
            padding: 0.95rem 1rem;
        }

        .gm-progress-subject + .gm-progress-subject {
            border-top: 1px solid #e2e8f0;
            margin-top: 1rem;
            padding-top: 1rem;
        }

        .gm-progress-subject-header {
            align-items: baseline;
            display: flex;
            flex-wrap: wrap;
            gap: 0.25rem 0.65rem;
            justify-content: space-between;
            margin-bottom: 0.55rem;
        }

        .gm-progress-subject-title {
            color: #0f172a;
            font-size: 0.96rem;
            font-weight: 800;
        }

        .gm-progress-subject-summary,
        .gm-progress-topic-detail,
        .gm-progress-topic-accuracy {
            color: #64748b;
            font-size: 0.78rem;
        }

        .gm-progress-topic {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.85rem;
            padding: 0.72rem 0.78rem;
        }

        .gm-progress-topic + .gm-progress-topic {
            margin-top: 0.5rem;
        }

        .gm-progress-topic-heading {
            align-items: center;
            display: flex;
            gap: 0.5rem;
            justify-content: space-between;
        }

        .gm-progress-topic-title {
            color: #1e293b;
            font-size: 0.88rem;
            font-weight: 750;
        }

        .gm-progress-status {
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 800;
            padding: 0.18rem 0.48rem;
            white-space: nowrap;
        }

        .gm-progress-status--not-started { background: #e2e8f0; color: #475569; }
        .gm-progress-status--starting { background: #dbeafe; color: #1d4ed8; }
        .gm-progress-status--in-progress { background: #fef3c7; color: #a16207; }
        .gm-progress-status--complete { background: #dcfce7; color: #15803d; }

        .gm-progress-track {
            background: #dbeafe;
            border-radius: 999px;
            height: 0.48rem;
            margin: 0.5rem 0 0.42rem;
            overflow: hidden;
        }

        .gm-progress-fill {
            background: linear-gradient(90deg, #60a5fa, #2563eb);
            border-radius: inherit;
            height: 100%;
            min-width: 0;
        }

        .gm-progress-topic-footer {
            align-items: center;
            display: flex;
            flex-wrap: wrap;
            gap: 0.25rem 0.6rem;
            justify-content: space-between;
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


def _build_empty_state_html(
    message: str,
    *,
    title: str = "Gr\u00e1fico indispon\u00edvel por enquanto",
) -> str:
    return (
        '<section class="gm-stats-empty">'
        f'<div class="gm-stats-section-title">{escape(title)}</div>'
        f'<div class="gm-stats-empty-text">{escape(message)}</div>'
        "</section>"
    )


def _build_progress_overview_card_html(
    topic_progress: list[StudentTopicProgress],
) -> str:
    total_questions = sum(item.total_questions for item in topic_progress)
    answered_questions = sum(item.answered_questions for item in topic_progress)
    remaining_questions = max(total_questions - answered_questions, 0)
    completion_rate = _share(answered_questions, total_questions)
    return _build_metric_card_html(
        title="Perguntas resolvidas",
        value=f"{answered_questions} / {total_questions}",
        detail=(
            f"{remaining_questions} faltando \u00b7 "
            f"{_format_percent(completion_rate)} conclu\u00eddo"
        ),
        tone="progress",
    )


def _select_next_focus(
    topic_progress: list[StudentTopicProgress],
) -> StudentTopicProgress | None:
    incomplete_topics = [item for item in topic_progress if item.remaining_questions > 0]
    if not incomplete_topics:
        return None
    return min(
        incomplete_topics,
        key=lambda item: (
            -item.remaining_questions,
            item.accuracy_rate,
            _format_subject_progress_label(item.subject).casefold(),
            _format_topic_progress_label(item.topic).casefold(),
        ),
    )


def _build_next_focus_card_html(topic_progress: list[StudentTopicProgress]) -> str:
    next_focus = _select_next_focus(topic_progress)
    if next_focus is None:
        value = "Tudo conclu\u00eddo"
        detail = "Todas as perguntas ativas deste projeto foram resolvidas."
    else:
        value = _format_topic_progress_label(next_focus.topic)
        question_label = (
            "pergunta faltando"
            if next_focus.remaining_questions == 1
            else "perguntas faltando"
        )
        detail = (
            f"Pr\u00f3ximo foco: {value} \u2014 "
            f"{next_focus.remaining_questions} {question_label}."
        )
    return _build_metric_card_html(
        title="Pr\u00f3ximo foco sugerido",
        value=value,
        detail=detail,
        tone="neutral",
    )


def _build_topic_progress_html(topic_progress: list[StudentTopicProgress]) -> str:
    grouped_progress: dict[str, list[StudentTopicProgress]] = {}
    for item in topic_progress:
        subject_label = _format_subject_progress_label(item.subject)
        grouped_progress.setdefault(subject_label, []).append(item)

    html_parts = ['<section class="gm-progress-map">']
    for subject_label in sorted(grouped_progress, key=str.casefold):
        subject_topics = grouped_progress[subject_label]
        total_questions = sum(item.total_questions for item in subject_topics)
        answered_questions = sum(item.answered_questions for item in subject_topics)
        remaining_questions = max(total_questions - answered_questions, 0)
        html_parts.extend(
            [
                '<div class="gm-progress-subject">',
                '<div class="gm-progress-subject-header">',
                f'<div class="gm-progress-subject-title">{escape(subject_label)}</div>',
                '<div class="gm-progress-subject-summary">'
                f"{answered_questions}/{total_questions} conclu\u00eddas \u00b7 "
                f"{remaining_questions} faltando"
                "</div>",
                "</div>",
            ]
        )
        for item in sorted(
            subject_topics,
            key=lambda progress: _format_topic_progress_label(progress.topic).casefold(),
        ):
            topic_label = _format_topic_progress_label(item.topic)
            status_label, status_key = _progress_status(item.completion_rate)
            completion_percent = max(min(item.completion_rate, 1.0), 0.0) * 100
            if item.total_answers > 0:
                accuracy_detail = (
                    f"Acur\u00e1cia: {_format_percent(item.accuracy_rate)} "
                    f"em {item.total_answers} tentativas"
                )
            else:
                accuracy_detail = "Ainda n\u00e3o iniciado"
            html_parts.extend(
                [
                    '<div class="gm-progress-topic">',
                    '<div class="gm-progress-topic-heading">',
                    f'<div class="gm-progress-topic-title">{escape(topic_label)}</div>',
                    f'<span class="gm-progress-status gm-progress-status--{status_key}">'
                    f"{escape(status_label)}</span>",
                    "</div>",
                    '<div class="gm-progress-track" aria-hidden="true">',
                    f'<div class="gm-progress-fill" style="width: {completion_percent:.1f}%"></div>',
                    "</div>",
                    '<div class="gm-progress-topic-footer">',
                    '<div class="gm-progress-topic-detail">'
                    f"{item.answered_questions} / {item.total_questions} resolvidas \u00b7 "
                    f"{item.remaining_questions} faltando"
                    "</div>",
                    f'<div class="gm-progress-topic-accuracy">{escape(accuracy_detail)}</div>',
                    "</div>",
                    "</div>",
                ]
            )
        html_parts.append("</div>")
    html_parts.append("</section>")
    return "".join(html_parts)


def _progress_status(completion_rate: float) -> tuple[str, str]:
    normalized_rate = max(min(completion_rate, 1.0), 0.0)
    if normalized_rate <= 0:
        return "N\u00e3o iniciado", "not-started"
    if normalized_rate < 0.5:
        return "Come\u00e7ando", "starting"
    if normalized_rate < 1:
        return "Em andamento", "in-progress"
    return "Conclu\u00eddo", "complete"


def _build_subject_performance_chart(
    subject_performance: list[StudentSubjectPerformance],
    *,
    topic_progress: list[StudentTopicProgress] | None = None,
) -> alt.LayerChart:
    progress_by_topic = _aggregate_progress_by_topic(topic_progress or [])
    chart_rows: list[dict[str, object]] = []
    for item in subject_performance:
        topic_label = _format_subject_stat_label(item.topic)
        progress = progress_by_topic.get(normalize_taxonomy_value(item.topic))
        chart_rows.append(
            {
                "topic_label": topic_label,
                "topic_axis_label": _wrap_chart_axis_label(topic_label),
                "accuracy_percent": round(item.accuracy_rate * 100, 1),
                "total_answers": item.total_answers,
                "total_correct": item.total_correct,
                "total_wrong": item.total_wrong,
                "average_time_label": _format_duration(item.average_time_spent_seconds),
                "completion_label": (
                    _format_percent(float(progress["completion_rate"]))
                    if progress is not None
                    else "Sem dados"
                ),
                "answered_questions": progress["answered_questions"] if progress else 0,
                "total_questions": progress["total_questions"] if progress else 0,
                "remaining_questions": progress["remaining_questions"] if progress else 0,
            }
        )

    chart_data = pd.DataFrame(chart_rows)
    topic_order = chart_data["topic_axis_label"].tolist()

    base = alt.Chart(chart_data).encode(
        x=alt.X(
            "topic_axis_label:N",
            sort=topic_order,
            axis=alt.Axis(
                title="T\u00f3picos",
                labelAngle=0,
                labelLimit=220,
                labelLineHeight=16,
                labelOverlap=False,
            ),
        )
    )
    tooltip = [
        alt.Tooltip("topic_label:N", title="T\u00f3pico"),
        alt.Tooltip("accuracy_percent:Q", title="% de acerto", format=".1f"),
        alt.Tooltip("total_correct:Q", title="Acertos"),
        alt.Tooltip("total_wrong:Q", title="Erros"),
        alt.Tooltip("total_answers:Q", title="Tentativas"),
        alt.Tooltip("average_time_label:N", title="Tempo m\u00e9dio"),
        alt.Tooltip("completion_label:N", title="Conclus\u00e3o"),
        alt.Tooltip("answered_questions:Q", title="Perguntas resolvidas"),
        alt.Tooltip("total_questions:Q", title="Perguntas ativas"),
        alt.Tooltip("remaining_questions:Q", title="Perguntas restantes"),
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


def _aggregate_progress_by_topic(
    topic_progress: list[StudentTopicProgress],
) -> dict[str | None, dict[str, float | int]]:
    totals: dict[str | None, dict[str, float | int]] = {}
    for item in topic_progress:
        topic_key = normalize_taxonomy_value(item.topic)
        aggregate = totals.setdefault(
            topic_key,
            {
                "total_questions": 0,
                "answered_questions": 0,
                "remaining_questions": 0,
                "completion_rate": 0.0,
            },
        )
        aggregate["total_questions"] += item.total_questions
        aggregate["answered_questions"] += item.answered_questions
        aggregate["remaining_questions"] += item.remaining_questions

    for aggregate in totals.values():
        aggregate["completion_rate"] = _share(
            int(aggregate["answered_questions"]),
            int(aggregate["total_questions"]),
        )
    return totals


def _format_subject_stat_label(subject: str | None) -> str:
    formatted_subject = format_topic_label(subject)
    if formatted_subject:
        return formatted_subject
    return "Sem t\u00f3pico"


def _format_subject_progress_label(subject: str | None) -> str:
    return format_subject_label(subject) or "Sem mat\u00e9ria"


def _format_topic_progress_label(topic: str | None) -> str:
    return format_topic_label(topic) or "Sem t\u00f3pico"


def _wrap_chart_axis_label(label: str, *, max_line_length: int = 20) -> str:
    stripped_label = label.strip()
    if not stripped_label:
        return label

    wrapped_lines = wrap(
        stripped_label,
        width=max_line_length,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped_lines:
        return stripped_label
    return "\n".join(wrapped_lines)


def _share(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(min(part / total, 1.0), 0.0)


def _format_percent(value: float) -> str:
    return f"{max(min(value, 1.0), 0.0) * 100:.1f}%"


def _format_duration(seconds: float) -> str:
    return format_elapsed_time(int(round(max(seconds or 0.0, 0.0))))
