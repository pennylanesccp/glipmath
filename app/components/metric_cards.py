from __future__ import annotations

import streamlit as st


def render_metric_cards(
    *,
    day_streak: int,
    question_streak: int,
    leaderboard_position: str,
) -> None:
    """Render the top gamification metrics."""

    streak_day_column, streak_question_column, leaderboard_column = st.columns(3)
    streak_day_column.metric("Day streak", day_streak)
    streak_question_column.metric("Question streak", question_streak)
    leaderboard_column.metric("Leaderboard", leaderboard_position)
