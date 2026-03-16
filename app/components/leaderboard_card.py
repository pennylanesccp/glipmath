from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.domain.models import LeaderboardEntry


def render_leaderboard(
    leaderboard: list[LeaderboardEntry],
    *,
    current_user_email: str,
    limit: int = 5,
) -> None:
    """Render a compact leaderboard table."""

    st.subheader("Ranking")
    if not leaderboard:
        st.info("O ranking ainda nao tem participantes.")
        return

    rows: list[dict[str, object]] = []
    for entry in leaderboard[:limit]:
        display_name = entry.display_name
        if entry.user_email == current_user_email:
            display_name = f"{display_name} (voce)"
        rows.append(
            {
                "Posicao": f"#{entry.rank}",
                "Aluno": display_name,
                "Acertos": entry.total_correct,
                "Respostas": entry.total_answers,
            }
        )

    st.table(pd.DataFrame(rows))
