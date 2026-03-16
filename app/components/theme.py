from __future__ import annotations

import streamlit as st

from app.components.navigation import build_query_link, get_query_param
from app.state.session_state import get_theme_mode, set_theme_mode

THEMES = {
    "dark": {
        "background": "#0b1220",
        "surface": "#111a2c",
        "surface_soft": "#182338",
        "surface_alt": "#1b2840",
        "text_main": "#eef2ff",
        "text_secondary": "#b8c2e0",
        "border": "rgba(255, 255, 255, 0.08)",
        "border_strong": "rgba(255, 255, 255, 0.16)",
        "primary": "#4f46e5",
        "primary_light": "rgba(99, 102, 241, 0.18)",
        "primary_shadow": "0 8px 20px -6px rgba(79, 70, 229, 0.45)",
        "shadow_soft": "0 8px 30px rgba(0, 0, 0, 0.28)",
        "shadow_card": "0 24px 56px rgba(0, 0, 0, 0.34)",
        "success": "#4ade80",
        "success_bg": "rgba(34, 197, 94, 0.12)",
        "success_border": "rgba(74, 222, 128, 0.32)",
        "error": "#f87171",
        "error_bg": "rgba(248, 113, 113, 0.12)",
        "error_border": "rgba(248, 113, 113, 0.3)",
        "chip_fire": "#fb923c",
        "chip_podium": "#facc15",
        "google_background": "#131314",
        "google_border": "#8e918f",
        "google_text": "#e3e3e3",
        "toggle_track": "#1e293b",
        "toggle_thumb": "#f8fafc",
        "toggle_icon": "#1e293b",
        "logout_text": "#cbd5f5",
    },
    "light": {
        "background": "#f8fafc",
        "surface": "#ffffff",
        "surface_soft": "#ffffff",
        "surface_alt": "#eef2ff",
        "text_main": "#0f172a",
        "text_secondary": "#475569",
        "border": "#e2e8f0",
        "border_strong": "#cbd5e1",
        "primary": "#4f46e5",
        "primary_light": "#eef2ff",
        "primary_shadow": "0 8px 20px -6px rgba(79, 70, 229, 0.4)",
        "shadow_soft": "0 8px 30px rgba(15, 23, 42, 0.06)",
        "shadow_card": "0 20px 48px rgba(15, 23, 42, 0.08)",
        "success": "#16a34a",
        "success_bg": "#f0fdf4",
        "success_border": "#bbf7d0",
        "error": "#dc2626",
        "error_bg": "#fef2f2",
        "error_border": "#fecaca",
        "chip_fire": "#f97316",
        "chip_podium": "#eab308",
        "google_background": "#ffffff",
        "google_border": "#747775",
        "google_text": "#1f1f1f",
        "toggle_track": "#dbe4ff",
        "toggle_thumb": "#4f46e5",
        "toggle_icon": "#ffffff",
        "logout_text": "#475569",
    },
}


def current_theme_mode() -> str:
    """Return the effective theme mode, syncing with the URL when present."""

    requested_theme = get_query_param("theme")
    if requested_theme in THEMES and requested_theme != get_theme_mode():
        set_theme_mode(requested_theme)
    return get_theme_mode()


def current_palette() -> dict[str, str]:
    """Return the active UI palette."""

    return THEMES[current_theme_mode()]


def apply_app_theme() -> None:
    """Apply the current theme and template-driven UI styling."""

    palette = current_palette()
    st.markdown(
        f"""
        <style>
        :root {{
            --gm-bg: {palette["background"]};
            --gm-surface: {palette["surface"]};
            --gm-surface-soft: {palette["surface_soft"]};
            --gm-surface-alt: {palette["surface_alt"]};
            --gm-text-main: {palette["text_main"]};
            --gm-text-secondary: {palette["text_secondary"]};
            --gm-border: {palette["border"]};
            --gm-border-strong: {palette["border_strong"]};
            --gm-primary: {palette["primary"]};
            --gm-primary-light: {palette["primary_light"]};
            --gm-primary-shadow: {palette["primary_shadow"]};
            --gm-shadow-soft: {palette["shadow_soft"]};
            --gm-shadow-card: {palette["shadow_card"]};
            --gm-success: {palette["success"]};
            --gm-success-bg: {palette["success_bg"]};
            --gm-success-border: {palette["success_border"]};
            --gm-error: {palette["error"]};
            --gm-error-bg: {palette["error_bg"]};
            --gm-error-border: {palette["error_border"]};
            --gm-chip-fire: {palette["chip_fire"]};
            --gm-chip-podium: {palette["chip_podium"]};
            --gm-google-background: {palette["google_background"]};
            --gm-google-border: {palette["google_border"]};
            --gm-google-text: {palette["google_text"]};
            --gm-toggle-track: {palette["toggle_track"]};
            --gm-toggle-thumb: {palette["toggle_thumb"]};
            --gm-toggle-icon: {palette["toggle_icon"]};
            --gm-logout-text: {palette["logout_text"]};
        }}

        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        [data-testid="stStatusWidget"] {{
            display: none !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at top, rgba(79, 70, 229, 0.12), transparent 28%),
                linear-gradient(180deg, var(--gm-bg) 0%, var(--gm-bg) 100%);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        section.main > div {{
            max-width: 480px;
        }}

        .block-container {{
            max-width: 480px;
            padding: 18px 18px 32px;
        }}

        @media (max-width: 420px) {{
            .block-container {{
                padding: 14px 14px 28px;
            }}
        }}

        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] span,
        [data-testid="stAppViewContainer"] div,
        [data-testid="stAppViewContainer"] label {{
            color: var(--gm-text-main);
        }}

        [data-testid="stMarkdownContainer"] p {{
            margin-bottom: 0;
        }}

        .stAlert {{
            border-radius: 18px;
        }}

        .stAlert [data-testid="stMarkdownContainer"] p {{
            line-height: 1.5;
        }}

        div.st-key-glipmath_subject_filter label {{
            display: none !important;
        }}

        div.st-key-glipmath_subject_filter {{
            margin-bottom: 0;
        }}

        div.st-key-glipmath_subject_filter [data-baseweb="select"] > div {{
            align-items: center;
            background: var(--gm-surface);
            border: 1px solid var(--gm-border);
            border-radius: 999px;
            box-shadow: var(--gm-shadow-soft);
            min-height: 42px;
            padding-left: 4px;
        }}

        div.st-key-glipmath_subject_filter [data-baseweb="select"] * {{
            color: var(--gm-text-main);
            font-weight: 700;
        }}

        div.st-key-glipmath_subject_filter [data-baseweb="select"] svg {{
            color: var(--gm-text-secondary);
        }}

        .gm-login-shell {{
            min-height: calc(100vh - 72px);
            padding-top: 6px;
            position: relative;
        }}

        .gm-login-card {{
            align-items: center;
            background: var(--gm-surface);
            border: 1px solid var(--gm-border);
            border-radius: 28px;
            box-shadow: var(--gm-shadow-card);
            display: flex;
            flex-direction: column;
            gap: 28px;
            justify-content: center;
            margin-top: 84px;
            padding: 32px 22px 26px;
            width: 100%;
        }}

        .gm-logo {{
            display: block;
            height: auto;
            margin: 0 auto;
            max-width: min(100%, 320px);
            width: 100%;
        }}

        .gm-theme-toggle-wrap {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 12px;
        }}

        .gm-theme-toggle {{
            background: var(--gm-toggle-track);
            border-radius: 999px;
            box-shadow: var(--gm-shadow-soft);
            display: inline-flex;
            height: 40px;
            position: relative;
            text-decoration: none;
            width: 72px;
        }}

        .gm-theme-toggle-thumb {{
            align-items: center;
            background: var(--gm-toggle-thumb);
            border-radius: 50%;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.18);
            display: flex;
            height: 32px;
            justify-content: center;
            left: 4px;
            position: absolute;
            top: 4px;
            transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
            width: 32px;
        }}

        .gm-theme-toggle--dark .gm-theme-toggle-thumb {{
            transform: translateX(32px);
        }}

        .gm-theme-icon {{
            color: var(--gm-toggle-icon);
            height: 16px;
            position: absolute;
            transition: opacity 0.2s ease, transform 0.28s ease;
            width: 16px;
        }}

        .gm-theme-icon--sun {{
            opacity: 1;
            transform: scale(1);
        }}

        .gm-theme-icon--moon {{
            opacity: 0;
            transform: scale(0.6);
        }}

        .gm-theme-toggle--dark .gm-theme-icon--sun {{
            opacity: 0;
            transform: scale(0.6);
        }}

        .gm-theme-toggle--dark .gm-theme-icon--moon {{
            opacity: 1;
            transform: scale(1);
        }}

        .gm-google-button {{
            align-items: center;
            background: var(--gm-google-background);
            border: 1px solid var(--gm-google-border);
            border-radius: 999px;
            box-shadow: var(--gm-shadow-soft);
            color: var(--gm-google-text);
            display: inline-flex;
            font-family: Roboto, Arial, sans-serif;
            font-size: 14px;
            font-weight: 500;
            gap: 10px;
            justify-content: center;
            min-height: 40px;
            padding: 10px 14px;
            text-decoration: none;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            width: min(100%, 320px);
        }}

        .gm-google-button:hover {{
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.10);
            transform: translateY(-1px);
        }}

        .gm-google-button:active {{
            transform: translateY(1px);
        }}

        .gm-google-button.is-disabled {{
            opacity: 0.58;
            pointer-events: none;
        }}

        .gm-google-icon {{
            display: block;
            flex: 0 0 auto;
            height: 18px;
            width: 18px;
        }}

        .gm-top-row {{
            align-items: center;
            display: flex;
            gap: 12px;
            margin-bottom: 10px;
        }}

        .gm-status-row {{
            align-items: center;
            display: flex;
            gap: 10px;
            margin-bottom: 18px;
        }}

        .gm-chip-group {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .gm-chip {{
            align-items: center;
            background: var(--gm-surface);
            border: 1px solid var(--gm-border);
            border-radius: 999px;
            box-shadow: var(--gm-shadow-soft);
            color: var(--gm-text-main);
            display: inline-flex;
            font-size: 13px;
            font-weight: 800;
            gap: 7px;
            min-height: 36px;
            padding: 6px 12px;
            white-space: nowrap;
        }}

        .gm-chip img {{
            display: block;
            height: 16px;
            width: 16px;
        }}

        .gm-chip--fire img {{
            filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.08));
        }}

        .gm-logout-link {{
            color: var(--gm-logout-text);
            font-size: 13px;
            font-weight: 800;
            padding: 10px 0;
            text-align: right;
            text-decoration: none;
            white-space: nowrap;
        }}

        .gm-question-card {{
            background: var(--gm-surface);
            border: 1px solid var(--gm-border);
            border-radius: 24px;
            box-shadow: var(--gm-shadow-card);
            margin-bottom: 20px;
            padding: 28px 24px;
        }}

        .gm-question-statement {{
            color: var(--gm-text-main);
            font-size: 18px;
            font-weight: 500;
            line-height: 1.65;
        }}

        .gm-options {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .gm-option,
        .gm-option:visited {{
            background: var(--gm-surface);
            border: 2px solid var(--gm-border);
            border-radius: 16px;
            color: inherit;
            display: flex;
            gap: 16px;
            overflow: hidden;
            padding: 18px 20px;
            position: relative;
            text-decoration: none;
            transition: transform 0.18s ease, border-color 0.22s ease, background 0.22s ease;
        }}

        .gm-option:hover {{
            transform: translateY(-1px);
        }}

        .gm-option-radio {{
            align-items: center;
            border: 2px solid var(--gm-border-strong);
            border-radius: 50%;
            display: inline-flex;
            flex: 0 0 auto;
            height: 24px;
            justify-content: center;
            margin-top: 1px;
            width: 24px;
        }}

        .gm-option-radio::after {{
            background: var(--gm-primary);
            border-radius: 50%;
            content: "";
            height: 10px;
            transform: scale(0);
            transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
            width: 10px;
        }}

        .gm-option-content {{
            display: flex;
            flex: 1 1 auto;
            flex-direction: column;
            gap: 10px;
            min-width: 0;
        }}

        .gm-option-text {{
            color: var(--gm-text-secondary);
            font-size: 16px;
            font-weight: 600;
            line-height: 1.45;
        }}

        .gm-option-explanation {{
            border-top: 1px solid rgba(15, 23, 42, 0.08);
            color: var(--gm-text-secondary);
            font-size: 14px;
            line-height: 1.55;
            padding-top: 10px;
        }}

        .gm-option--selected {{
            background: var(--gm-primary-light);
            border-color: var(--gm-primary);
        }}

        .gm-option--selected .gm-option-radio {{
            border-color: var(--gm-primary);
        }}

        .gm-option--selected .gm-option-radio::after {{
            transform: scale(1);
        }}

        .gm-option--selected .gm-option-text {{
            color: var(--gm-primary);
        }}

        .gm-option--correct {{
            background: var(--gm-success-bg);
            border-color: var(--gm-success);
        }}

        .gm-option--correct .gm-option-radio {{
            border-color: var(--gm-success);
        }}

        .gm-option--correct .gm-option-radio::after {{
            background: var(--gm-success);
            transform: scale(1);
        }}

        .gm-option--correct .gm-option-text,
        .gm-option--correct .gm-option-explanation {{
            color: var(--gm-success);
        }}

        .gm-option--correct .gm-option-text {{
            font-weight: 800;
        }}

        .gm-option--wrong,
        .gm-option--wrong-selected {{
            background: var(--gm-error-bg);
            border-color: var(--gm-error);
        }}

        .gm-option--wrong .gm-option-text,
        .gm-option--wrong .gm-option-explanation,
        .gm-option--wrong-selected .gm-option-text,
        .gm-option--wrong-selected .gm-option-explanation {{
            color: var(--gm-error);
        }}

        .gm-option--wrong .gm-option-text,
        .gm-option--wrong-selected .gm-option-text {{
            font-weight: 800;
        }}

        .gm-option--wrong-selected .gm-option-radio {{
            border-color: var(--gm-error);
        }}

        .gm-option--wrong-selected .gm-option-radio::after {{
            background: var(--gm-error);
            transform: scale(1);
        }}

        .gm-option--neutral {{
            background: var(--gm-surface);
            border-color: var(--gm-border);
        }}

        .gm-bottom-action {{
            background: linear-gradient(to top, var(--gm-bg) 72%, transparent);
            bottom: 0;
            margin-top: 18px;
            padding: 16px 0 10px;
            position: sticky;
        }}

        .gm-bottom-action-row {{
            align-items: center;
            display: flex;
            gap: 16px;
            justify-content: space-between;
        }}

        .gm-link-button {{
            border-radius: 16px;
            display: inline-flex;
            font-size: 16px;
            font-weight: 800;
            justify-content: center;
            min-height: 54px;
            padding: 16px 18px;
            text-decoration: none;
        }}

        .gm-link-button--skip {{
            color: var(--gm-text-secondary);
            min-height: auto;
            padding: 8px 4px;
        }}

        .gm-link-button--primary {{
            background: var(--gm-primary);
            box-shadow: var(--gm-primary-shadow);
            color: #ffffff;
            flex: 1 1 auto;
        }}

        .gm-link-button--primary.is-disabled {{
            background: #cbd5e1;
            box-shadow: none;
            color: #f8fafc;
            pointer-events: none;
        }}

        .gm-result-card {{
            align-items: center;
            background: var(--gm-error-bg);
            border: 1px solid var(--gm-error-border);
            border-radius: 16px;
            box-shadow: var(--gm-shadow-soft);
            color: var(--gm-error);
            display: inline-flex;
            flex: 0 0 auto;
            font-size: 15px;
            font-weight: 800;
            min-height: 44px;
            padding: 10px 14px;
        }}

        .gm-result-card--correct {{
            background: var(--gm-success-bg);
            border-color: var(--gm-success-border);
            color: var(--gm-success);
        }}

        .gm-info-card {{
            background: var(--gm-surface);
            border: 1px solid var(--gm-border);
            border-radius: 18px;
            box-shadow: var(--gm-shadow-soft);
            color: var(--gm-text-secondary);
            font-size: 15px;
            line-height: 1.55;
            padding: 18px;
        }}

        @media (max-width: 420px) {{
            .gm-login-card {{
                border-radius: 24px;
                gap: 24px;
                margin-top: 72px;
                padding: 28px 18px 22px;
            }}

            .gm-logo {{
                max-width: min(100%, 280px);
            }}

            .gm-question-card {{
                border-radius: 22px;
                margin-bottom: 16px;
                padding: 24px 20px;
            }}

            .gm-question-statement {{
                font-size: 17px;
            }}

            .gm-option,
            .gm-option:visited {{
                padding: 16px;
            }}

            .gm-option-text {{
                font-size: 15px;
            }}

            .gm-option-explanation {{
                font-size: 14px;
            }}

            .gm-chip {{
                font-size: 12px;
                min-height: 34px;
                padding: 6px 10px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_theme_toggle_markup() -> str:
    """Return the template-inspired light/dark toggle markup."""

    mode = current_theme_mode()
    target_mode = "light" if mode == "dark" else "dark"
    href = build_query_link(theme=target_mode)
    return f"""
    <div class="gm-theme-toggle-wrap">
        <a
            class="gm-theme-toggle gm-theme-toggle--{mode}"
            href="{href}"
            aria-label="Alternar entre modo claro e escuro"
        >
            <span class="gm-theme-toggle-thumb">
                <svg class="gm-theme-icon gm-theme-icon--sun" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="12" cy="12" r="4.2" fill="currentColor"></circle>
                    <path d="M12 2.5V5.2M12 18.8V21.5M21.5 12H18.8M5.2 12H2.5M18.72 5.28L16.8 7.2M7.2 16.8L5.28 18.72M18.72 18.72L16.8 16.8M7.2 7.2L5.28 5.28" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
                </svg>
                <svg class="gm-theme-icon gm-theme-icon--moon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M20.2 14.2A8.7 8.7 0 0 1 9.8 3.8 9.2 9.2 0 1 0 20.2 14.2Z"></path>
                </svg>
            </span>
        </a>
    </div>
    """
