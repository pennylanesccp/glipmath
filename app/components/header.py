from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.components.navigation import build_query_link
from app.components.template_assets import get_template_asset_data_uri
from app.components.theme import render_theme_toggle_markup
from app.components.timer_chip import render_timer_chip


@dataclass(frozen=True, slots=True)
class PracticeHeaderMetrics:
    """Compact metrics rendered in the question-screen header."""

    day_streak: int
    question_streak: int
    leaderboard_position: str


def render_question_header(
    *,
    base_dir: str,
    subject_options: list[str],
    selected_subject: str,
    metrics: PracticeHeaderMetrics,
    elapsed_seconds: float,
    timer_running: bool,
) -> str:
    """Render the template-inspired question header and return the selected subject."""

    top_left, top_right = st.columns([3.2, 1.1])
    with top_left:
        if selected_subject not in subject_options:
            subject_options = ["Todas", *[option for option in subject_options if option != "Todas"]]
            selected_subject = "Todas"

        selected_value = st.selectbox(
            "Disciplina",
            options=subject_options,
            index=subject_options.index(selected_subject),
            key="glipmath_subject_filter",
            label_visibility="collapsed",
        )
    with top_right:
        st.markdown(render_theme_toggle_markup(), unsafe_allow_html=True)

    chips_column, timer_column, logout_column = st.columns([2.35, 1.2, 0.85])
    with chips_column:
        fire_icon = get_template_asset_data_uri(base_dir, "fire-svgrepo-com.svg")
        podium_icon = get_template_asset_data_uri(base_dir, "pedestal-podium-svgrepo-com.svg")
        st.markdown(
            f"""
            <div class="gm-chip-group">
                <div class="gm-chip gm-chip--fire">
                    <img src="{fire_icon}" alt="" aria-hidden="true" />
                    <span>{_format_streak_text(metrics.day_streak, metrics.question_streak)}</span>
                </div>
                <div class="gm-chip">
                    <img src="{podium_icon}" alt="" aria-hidden="true" />
                    <span>{_compact_position(metrics.leaderboard_position)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with timer_column:
        render_timer_chip(
            base_dir=base_dir,
            elapsed_seconds=elapsed_seconds,
            running=timer_running,
        )
    with logout_column:
        st.markdown(
            f'<a class="gm-logout-link" href="{build_query_link(glipmath_action="logout")}">Sair</a>',
            unsafe_allow_html=True,
        )

    return selected_value


def _compact_position(position: str) -> str:
    return position.replace(" / ", "/")


def _format_streak_text(day_streak: int, question_streak: int) -> str:
    return f"{max(day_streak, 0)}d / {max(question_streak, 0)}x"
