from __future__ import annotations

import math

import streamlit.components.v1 as components

from app.components.template_assets import get_template_asset_data_uri
from app.components.theme import current_palette


def format_elapsed_time(total_seconds: float) -> str:
    """Format elapsed time for the compact timer chip."""

    safe_seconds = max(int(math.floor(total_seconds)), 0)
    minutes, seconds = divmod(safe_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def render_timer_chip(
    *,
    base_dir: str,
    elapsed_seconds: float,
    running: bool,
) -> None:
    """Render a lightweight live timer chip without forcing Streamlit reruns."""

    palette = current_palette()
    icon_uri = get_template_asset_data_uri(base_dir, "timer-outline-svgrepo-com.svg")
    initial_label = format_elapsed_time(elapsed_seconds)
    components.html(
        f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="utf-8" />
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    overflow: hidden;
                }}

                .gm-timer-chip {{
                    align-items: center;
                    background: {palette["surface"]};
                    border: 1px solid {palette["border"]};
                    border-radius: 999px;
                    box-shadow: {palette["shadow_soft"]};
                    color: {palette["text_main"]};
                    display: inline-flex;
                    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                    font-size: 13px;
                    font-weight: 800;
                    gap: 8px;
                    justify-content: center;
                    min-height: 36px;
                    min-width: 92px;
                    padding: 6px 12px;
                    white-space: nowrap;
                }}

                .gm-timer-chip img {{
                    display: block;
                    height: 16px;
                    width: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="gm-timer-chip">
                <img src="{icon_uri}" alt="" aria-hidden="true" />
                <span id="gm-timer-value">{initial_label}</span>
            </div>
            <script>
                const timerElement = document.getElementById("gm-timer-value");
                let elapsed = {int(max(elapsed_seconds, 0.0))};
                const running = {str(bool(running)).lower()};

                function formatElapsed(totalSeconds) {{
                    const safeSeconds = Math.max(totalSeconds, 0);
                    const seconds = safeSeconds % 60;
                    const totalMinutes = Math.floor(safeSeconds / 60);
                    const minutes = totalMinutes % 60;
                    const hours = Math.floor(totalMinutes / 60);
                    if (hours > 0) {{
                        return `${{hours}}:${{String(minutes).padStart(2, "0")}}:${{String(seconds).padStart(2, "0")}}`;
                    }}
                    return `${{String(minutes).padStart(2, "0")}}:${{String(seconds).padStart(2, "0")}}`;
                }}

                timerElement.textContent = formatElapsed(elapsed);
                if (running) {{
                    window.setInterval(() => {{
                        elapsed += 1;
                        timerElement.textContent = formatElapsed(elapsed);
                    }}, 1000);
                }}
            </script>
        </body>
        </html>
        """,
        height=42,
    )
