from __future__ import annotations

import streamlit as st


def render_metric_cards(
    *,
    day_streak: int,
    question_streak: int,
    leaderboard_position: str,
) -> None:
    """Render the top gamification metrics."""

    day_column, question_column, leaderboard_column = st.columns(3)
    day_column.metric("Sequencia diaria", day_streak)
    question_column.metric("Sequencia de acertos", question_streak)
    leaderboard_column.metric("Posicao no ranking", leaderboard_position)
