from __future__ import annotations

import streamlit as st

QUIZ_BLOCK_GAP = "12px"
QUIZ_COMPACT_GAP = "6px"
QUIZ_OPTION_GAP = QUIZ_COMPACT_GAP
QUIZ_ALTERNATIVE_LABEL_GAP = QUIZ_COMPACT_GAP
QUIZ_LAYOUT_SPACING = {
    "mobile": {
        "page_top_to_status": QUIZ_BLOCK_GAP,
        "status_to_question": QUIZ_BLOCK_GAP,
        "question_to_alternatives": QUIZ_BLOCK_GAP,
        "alternative_label_to_options": QUIZ_ALTERNATIVE_LABEL_GAP,
        "option_gap": QUIZ_OPTION_GAP,
        "alternatives_to_actions": QUIZ_BLOCK_GAP,
        "page_bottom": "20px",
    },
    "desktop": {
        "page_top_to_status": "12px",
        "status_to_question": QUIZ_BLOCK_GAP,
        "question_to_alternatives": QUIZ_BLOCK_GAP,
        "alternative_label_to_options": QUIZ_ALTERNATIVE_LABEL_GAP,
        "option_gap": QUIZ_OPTION_GAP,
        "alternatives_to_actions": QUIZ_BLOCK_GAP,
        "page_bottom": "28px",
    },
}
QUIZ_LAYOUT_SPACING_VARIABLES = {
    "page_top_to_status": "--gm-quiz-page-top-to-status",
    "status_to_question": "--gm-quiz-status-to-question",
    "question_to_alternatives": "--gm-quiz-question-to-alternatives",
    "alternative_label_to_options": "--gm-quiz-alternative-label-to-options",
    "option_gap": "--gm-quiz-option-gap",
    "alternatives_to_actions": "--gm-quiz-alternatives-to-actions",
    "page_bottom": "--gm-quiz-page-bottom",
}


def _build_quiz_layout_spacing_css() -> str:
    mobile_spacing = _build_quiz_layout_spacing_declarations("mobile", indent="            ")
    desktop_spacing = _build_quiz_layout_spacing_declarations("desktop", indent="                ")
    return (
        "        :root {\n"
        f"{mobile_spacing}\n"
        "        }\n\n"
        "        @media (min-width: 641px) {\n"
        "            :root {\n"
        f"{desktop_spacing}\n"
        "            }\n"
        "        }\n"
    )


def _build_quiz_layout_spacing_declarations(breakpoint: str, *, indent: str) -> str:
    spacing = QUIZ_LAYOUT_SPACING[breakpoint]
    return "\n".join(
        f"{indent}{css_variable}: {spacing[token]};"
        for token, css_variable in QUIZ_LAYOUT_SPACING_VARIABLES.items()
    )


def _apply_live_page_styles() -> None:
    st.markdown(
        (
            """
        <style>
"""
            + _build_quiz_layout_spacing_css()
            + """
        :root {
            --gm-wide-surface-width: 100%;
            --gm-narrow-surface-width: calc(100% - 12px);
            --gm-live-card-inline-padding: 12px;
            --gm-live-actions-to-review-gap: 12px;
            --gm-live-review-card-gap: 6px;
            --gm-live-review-to-actions-gap: 12px;
            --gm-pending-choice-content-gap: 6px;
            --gm-pending-choice-padding-block: 12px;
            --gm-pending-choice-padding-inline: 12px;
            --gm-quiz-action-button-gap: 6px;
            --gm-sidebar-section-gap: 0.24rem;
            --gm-sidebar-section-margin-bottom: 16px;
            --gm-sidebar-divider-margin-top: 0.05rem;
            --gm-sidebar-divider-margin-bottom: 0.72rem;
            --gm-sidebar-caption-margin-top: 0;
            --gm-sidebar-caption-margin-bottom: 0.24rem;
            --gm-sidebar-actions-gap: 0.3rem;
            --gm-sidebar-actions-padding-top: 0.45rem;
            --gm-sidebar-horizontal-padding: 1.25rem;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top, rgba(37, 99, 235, 0.12), transparent 26%),
                linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%) !important;
        }

        .block-container {
            max-width: 480px;
            padding-top: 0;
            padding-bottom: var(--gm-quiz-page-bottom);
        }

        .block-container > div[data-testid="stVerticalBlock"] {
            gap: 12px !important;
        }

        .block-container > div[data-testid="stVerticalBlock"]:has(.gm-quiz-status-block):has(.gm-quiz-question-block) {
            gap: 0 !important;
        }

        .st-key-gm_quiz_flow {
            gap: 0 !important;
        }

        .gm-quiz-section-gap {
            display: block;
            flex: 0 0 auto;
            font-size: 0;
            height: var(--gm-quiz-section-gap, 12px);
            line-height: 0;
            margin: 0;
            min-height: var(--gm-quiz-section-gap, 12px);
            padding: 0;
            width: 100%;
        }

        .gm-quiz-section-gap--after-question {
            --gm-quiz-section-gap: var(--gm-quiz-question-to-alternatives);
        }

        .gm-quiz-section-gap--before-pending-actions {
            --gm-quiz-section-gap: var(--gm-quiz-alternatives-to-actions);
        }

        .gm-quiz-section-gap--after-answer-actions {
            --gm-quiz-section-gap: var(--gm-live-actions-to-review-gap);
        }

        .gm-quiz-section-gap--between-answer-reviews {
            --gm-quiz-section-gap: var(--gm-live-review-card-gap);
        }

        .gm-quiz-section-gap--before-bottom-answer-actions {
            --gm-quiz-section-gap: var(--gm-live-review-to-actions-gap);
        }

        .block-container div[data-testid="stHorizontalBlock"] {
            gap: 6px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
            color: #0f172a;
        }

        section[data-testid="stSidebar"] {
            border-left: none !important;
            border-right: 1px solid #dbeafe !important;
            box-shadow: 18px 0 40px rgba(15, 23, 42, 0.1) !important;
        }

        section[data-testid="stSidebar"] > div {
            background: rgba(255, 255, 255, 0.96) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] p {
            color: #94a3b8 !important;
            font-size: 0.64rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.16em !important;
            line-height: 1.1 !important;
            text-transform: uppercase !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button {
            border-radius: 1rem;
        }

        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
            padding-left: var(--gm-sidebar-horizontal-padding) !important;
            padding-right: var(--gm-sidebar-horizontal-padding) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-section-hook) {
            gap: var(--gm-sidebar-section-gap) !important;
            margin-bottom: var(--gm-sidebar-section-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] .gm-sidebar-separator {
            background: #dbeafe;
            height: 1px;
            margin: 0.16rem 0 0.72rem;
            width: 100%;
        }

        section[data-testid="stSidebar"] .gm-sidebar-filter-separator-hook {
            margin-top: 0;
            margin-bottom: 0.78rem;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-section-hook) [data-testid="stCaptionContainer"] {
            margin: var(--gm-sidebar-caption-margin-top) 0 var(--gm-sidebar-caption-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) {
            gap: 0.34rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-testid="stMultiSelect"] {
            margin-bottom: 0.1rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-testid="stMultiSelect"] label {
            padding-bottom: 0.08rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-testid="stMultiSelect"] label p {
            color: #334155 !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-baseweb="select"] > div {
            background: #ffffff !important;
            border-color: #d7e0eb !important;
            border-radius: 0.78rem !important;
            min-height: 2.55rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-testid="stPopover"] > button {
            border-color: #d7e0eb !important;
            border-radius: 0.78rem !important;
            box-shadow: none !important;
            min-height: 2.55rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-subject-topic-filters-hook) [data-baseweb="select"] input::placeholder {
            color: #64748b !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) {
            gap: var(--gm-sidebar-actions-gap) !important;
            margin-top: 0.04rem !important;
            padding-top: 0.38rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) {
            gap: var(--gm-sidebar-actions-gap) !important;
            padding-top: var(--gm-sidebar-actions-padding-top) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button[kind="secondary"],
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"] {
            background: #fff4f4 !important;
            border: 1px solid #f5a3a3 !important;
            box-shadow: none !important;
            color: #b91c1c !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button *,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"] * {
            color: #b91c1c !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:hover,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:active,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"]:active {
            background: #fee2e2 !important;
            border-color: #f5a3a3 !important;
            box-shadow: none !important;
            color: #991b1b !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:focus,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:focus-visible,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"]:focus,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"]:focus-visible {
            background: #fff4f4 !important;
            border-color: #f5a3a3 !important;
            box-shadow: 0 0 0 0.16rem rgba(245, 163, 163, 0.32) !important;
            color: #b91c1c !important;
            outline: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:hover *,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > button:active *,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"]:hover *,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) [data-testid="stButton"] > [data-testid="baseButton-secondary"]:active * {
            color: #991b1b !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] p {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button:disabled,
        section[data-testid="stSidebar"] [data-testid="stButton"] > button[disabled] {
            background: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            color: #94a3b8 !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stButton"] > button:disabled p,
        section[data-testid="stSidebar"] [data-testid="stButton"] > button[disabled] p {
            color: #94a3b8 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) [data-testid="stButton"] > button,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) [data-testid="stButton"] > button[kind="secondary"] {
            background: #edf4ff !important;
            border: 1px solid #93c5fd !important;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.1) !important;
            color: #1d4ed8 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) [data-testid="stButton"] > button *,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) [data-testid="stButton"] > button:disabled *,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) [data-testid="stButton"] > button[disabled] * {
            color: #1d4ed8 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-apply-filters-hook) [data-testid="stButton"] > button:hover {
            background: #e2eeff !important;
            border-color: #60a5fa !important;
            color: #1d4ed8 !important;
        }

        .st-key-gm_quiz_pending_alternatives {
            gap: var(--gm-quiz-alternative-label-to-options) !important;
            margin-top: 0 !important;
            margin-left: auto !important;
            margin-right: auto !important;
            max-width: var(--gm-narrow-surface-width) !important;
            width: var(--gm-narrow-surface-width) !important;
        }

        .st-key-gm_quiz_answer_actions_top,
        .st-key-gm_quiz_answer_actions_bottom,
        .st-key-gm_quiz_pending_actions {
            gap: 0 !important;
            margin-left: auto !important;
            margin-right: auto !important;
            width: var(--gm-wide-surface-width) !important;
        }

        .st-key-gm_quiz_pending_actions {
            container-name: gm-quiz-pending-actions;
            container-type: inline-size;
        }

        .st-key-gm_quiz_answer_actions_top {
            margin: 0 !important;
        }

        .st-key-gm_quiz_answer_actions_bottom {
            margin: 0 !important;
        }

        .st-key-gm_quiz_answer_actions_top > div[data-testid="stHorizontalBlock"],
        .st-key-gm_quiz_answer_actions_bottom > div[data-testid="stHorizontalBlock"] {
            align-items: stretch !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
        }

        .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
        div[data-testid="stHorizontalBlock"] {
            align-items: stretch !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: var(--gm-quiz-action-button-gap) !important;
            width: 100% !important;
        }

        .st-key-gm_quiz_answer_actions_top > div[data-testid="stHorizontalBlock"] > div,
        .st-key-gm_quiz_answer_actions_bottom > div[data-testid="stHorizontalBlock"] > div,
        .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 0 !important;
            width: 0 !important;
        }

        .st-key-gm_quiz_answer_actions_top > div[data-testid="stHorizontalBlock"] > div:first-child,
        .st-key-gm_quiz_answer_actions_bottom > div[data-testid="stHorizontalBlock"] > div:first-child,
        .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child {
            flex: 1 1 0 !important;
        }

        .st-key-gm_quiz_answer_actions_top > div[data-testid="stHorizontalBlock"] > div:last-child,
        .st-key-gm_quiz_answer_actions_bottom > div[data-testid="stHorizontalBlock"] > div:last-child,
        .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
            flex: 2 1 0 !important;
        }

        .st-key-gm_quiz_answer_actions_top [data-testid="stButton"] > button,
        .st-key-gm_quiz_answer_actions_bottom [data-testid="stButton"] > button,
        .st-key-gm_quiz_pending_actions [data-testid="stButton"] > button {
            white-space: nowrap !important;
        }

        .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
        [data-testid="stButton"] > button {
            width: 100% !important;
        }

        @container gm-quiz-pending-actions (max-width: 330px) {
            .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
            }

            .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child,
            .st-key-gm_quiz_pending_actions:has(.gm-quiz-action-row-hook--pending)
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
                flex: 1 1 auto !important;
                width: 100% !important;
            }
        }

        .gm-live-metrics-bar {
            align-items: center;
            display: flex;
            gap: 6px;
            justify-content: center;
            width: 100%;
        }

        .gm-live-metric {
            align-items: center;
            appearance: none;
            background: transparent;
            border: 0;
            color: #1e3a8a;
            cursor: help;
            display: inline-flex;
            font-size: 1.12rem;
            font-weight: 800;
            gap: 6px;
            justify-content: flex-start;
            line-height: 1;
            padding: 0;
            position: relative;
            width: auto;
        }

        .gm-live-metric:focus {
            outline: none;
        }

        .gm-live-metric:focus-visible {
            box-shadow: 0 0 0 0.16rem rgba(37, 99, 235, 0.22);
            border-radius: 0.9rem;
        }

        .gm-live-metric-icon {
            display: block;
            flex: 0 0 auto;
            height: 1.42rem;
            width: 1.42rem;
        }

        .gm-live-metric-value {
            color: #1e3a8a;
            font-weight: 800;
            white-space: nowrap;
        }

        .gm-live-metric-tooltip {
            background: rgba(15, 23, 42, 0.94);
            border-radius: 0.8rem;
            bottom: calc(-100% - 0.55rem);
            color: #f8fafc;
            font-size: 0.73rem;
            font-weight: 600;
            left: 50%;
            line-height: 1.35;
            max-width: 10rem;
            opacity: 0;
            padding: 0.5rem 0.62rem;
            pointer-events: none;
            position: absolute;
            text-align: center;
            transform: translate(-50%, -0.18rem);
            transition: opacity 0.16s ease, transform 0.16s ease;
            white-space: normal;
            z-index: 20;
        }

        .gm-live-metric:hover .gm-live-metric-tooltip,
        .gm-live-metric:focus .gm-live-metric-tooltip,
        .gm-live-metric:focus-visible .gm-live-metric-tooltip,
        .gm-live-metric:active .gm-live-metric-tooltip {
            opacity: 1;
            transform: translate(-50%, 0);
        }

        .gm-live-metric--timer-warning,
        .gm-live-metric--timer-warning .gm-live-metric-value {
            color: #dc2626 !important;
        }

        .gm-live-metric--timer-warning .gm-live-metric-icon {
            filter: brightness(0) saturate(100%) invert(24%) sepia(97%) saturate(2652%) hue-rotate(351deg) brightness(89%) contrast(95%);
        }

        div[data-testid="stElementContainer"]:has(.gm-quiz-status-block) {
            align-items: center;
            box-sizing: border-box;
            display: flex;
            margin-top: var(--gm-quiz-page-top-to-status) !important;
            margin-bottom: 0 !important;
            width: 100%;
        }

        div[data-testid="stElementContainer"]:has(.gm-quiz-status-block) > div {
            width: 100%;
        }

        div[data-testid="stElementContainer"]:has(.gm-quiz-question-block) {
            margin-top: var(--gm-quiz-status-to-question) !important;
        }

        .gm-live-card {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1.25rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            margin-bottom: 0 !important;
            padding: 12px var(--gm-live-card-inline-padding);
        }

        .gm-live-question-card {
            box-sizing: border-box;
            margin-left: auto;
            margin-right: auto;
            max-width: var(--gm-wide-surface-width);
            width: var(--gm-wide-surface-width);
        }

        .gm-live-card-title {
            color: #475569;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 12px;
            text-transform: uppercase;
        }

        .gm-live-question-text,
        .gm-live-answer-text,
        .gm-live-answer-explanation,
        .gm-live-info-card {
            color: #0f172a;
            font-size: 0.98rem;
            line-height: 1.5;
        }

        .gm-live-question-text > :first-child,
        .gm-live-answer-text > :first-child,
        .gm-live-answer-explanation > :first-child {
            margin-top: 0;
        }

        .gm-live-question-text > :last-child,
        .gm-live-answer-text > :last-child,
        .gm-live-answer-explanation > :last-child {
            margin-bottom: 0;
        }

        .gm-live-question-text p,
        .gm-live-question-text ul,
        .gm-live-question-text ol,
        .gm-live-answer-text p,
        .gm-live-answer-text ul,
        .gm-live-answer-text ol,
        .gm-live-answer-explanation p,
        .gm-live-answer-explanation ul,
        .gm-live-answer-explanation ol {
            margin: 0 0 12px;
        }

        .gm-live-question-text pre,
        .gm-live-answer-text pre,
        .gm-live-answer-explanation pre {
            background: #0f172a;
            border-radius: 0.95rem;
            color: #e2e8f0;
            margin: 0.55rem 0;
            overflow-x: auto;
            padding: 0.85rem 0.95rem;
            white-space: pre-wrap;
        }

        .gm-live-question-text code,
        .gm-live-answer-text code,
        .gm-live-answer-explanation code {
            background: #eff6ff;
            border-radius: 0.45rem;
            color: #1e3a8a;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 0.94em;
            padding: 0.12rem 0.34rem;
        }

        .gm-live-question-text pre code,
        .gm-live-answer-text pre code,
        .gm-live-answer-explanation pre code {
            background: transparent;
            color: inherit;
            padding: 0;
        }

        .gm-question-board-controls {
            align-items: center;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            justify-content: center;
            margin-top: 0.7rem;
            width: 100%;
        }

        .gm-question-board-controls button {
            background: #edf4ff;
            border: 1px solid #93c5fd;
            border-radius: 0.85rem;
            color: #1d4ed8;
            cursor: pointer;
            font-weight: 700;
            min-height: 2.35rem;
            padding: 0.48rem 0.82rem;
        }

        .gm-live-answer-badge {
            color: #475569;
            font-size: 0.74rem;
            font-weight: 700;
            margin-bottom: 12px;
            text-transform: uppercase;
        }

        .gm-live-answer-card--correct {
            background: #f3fff6;
            border-color: #9ae6b4;
        }

        .gm-live-answer-card {
            margin-bottom: 0 !important;
            margin-left: auto;
            margin-right: auto;
            max-width: var(--gm-narrow-surface-width);
            width: var(--gm-narrow-surface-width);
        }

        .gm-live-pending-label {
            color: #7b8498;
            font-size: 0.88rem;
            font-weight: 600;
            margin: 0;
        }

        .gm-live-pending-choice-card {
            margin-bottom: 0 !important;
            max-width: none;
            padding: var(--gm-pending-choice-padding-block) var(--gm-pending-choice-padding-inline) !important;
            width: 100%;
        }

        .gm-live-pending-choice-link {
            color: inherit !important;
            cursor: pointer !important;
            display: block;
            margin: 0;
            text-decoration: none !important;
            width: 100%;
        }

        .gm-live-pending-choice-link:hover .gm-live-pending-choice-card {
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        .gm-live-pending-choice-link:focus-visible {
            outline: none;
        }

        .gm-live-pending-choice-link:focus-visible .gm-live-pending-choice-card {
            border-color: #60a5fa;
            box-shadow: 0 0 0 0.18rem rgba(96, 165, 250, 0.26);
        }

        .gm-live-pending-choice-row {
            align-items: flex-start;
            display: flex;
            gap: var(--gm-pending-choice-content-gap);
        }

        .gm-live-pending-choice-dot {
            background: #eef4ff;
            border: 1.5px solid #bfd4ff;
            border-radius: 999px;
            display: inline-block;
            flex: 0 0 auto;
            height: 1rem;
            margin-top: 0.18rem;
            width: 1rem;
        }

        .gm-live-pending-choice-dot--selected {
            background: #2563eb;
            border-color: #2563eb;
            box-shadow: inset 0 0 0 0.18rem #ffffff;
        }

        .gm-live-pending-choice-card--selected {
            background: #edf4ff;
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        .gm-live-pending-choice-card--selected .gm-live-answer-text {
            color: #1d4ed8;
        }

        .gm-live-answer-card--correct .gm-live-answer-badge,
        .gm-live-answer-card--correct .gm-live-answer-text,
        .gm-live-answer-card--correct .gm-live-answer-explanation {
            color: #166534;
        }

        .gm-live-answer-card--wrong {
            background: #fff4f4;
            border-color: #f5a3a3;
        }

        .gm-live-answer-card--wrong .gm-live-answer-badge,
        .gm-live-answer-card--wrong .gm-live-answer-text,
        .gm-live-answer-card--wrong .gm-live-answer-explanation {
            color: #b91c1c;
        }

        .gm-live-answer-explanation {
            border-top: 1px solid rgba(148, 163, 184, 0.22);
            margin-top: 12px;
            padding-top: 12px;
        }

        .gm-live-status-chip {
            align-items: center;
            border-radius: 1rem;
            display: flex;
            font-size: 0.96rem;
            font-weight: 800;
            justify-content: center;
            min-height: 3rem;
            width: 100%;
        }

        .gm-live-status-chip--correct {
            background: #f3fff6;
            border: 1px solid #9ae6b4;
            color: #166534;
        }

        .gm-live-status-chip--wrong {
            background: #fff4f4;
            border: 1px solid #f5a3a3;
            color: #b91c1c;
        }

        div[data-testid="stSelectbox"] label p,
        div[data-testid="stSelectbox"] label span {
            color: #334155 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stPopover"] > button {
            align-items: center;
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 999px !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06) !important;
            color: #0f172a !important;
            cursor: pointer !important;
            display: inline-flex !important;
            justify-content: space-between !important;
            min-height: 2.55rem !important;
            padding-inline: 0.95rem !important;
            text-align: left !important;
            width: 100% !important;
        }

        div[data-testid="stPopover"] > button * {
            color: #0f172a !important;
            font-weight: 500 !important;
        }

        div[data-testid="stPopover"] [data-testid="stPopoverBody"] {
            background: #ffffff !important;
        }

        div[data-testid="stPopover"] [data-testid="stPopoverBody"] > div,
        div[data-testid="stPopover"] div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stPopover"] div[data-testid="stVerticalBlockBorderWrapper"] > div,
        div[data-testid="stPopover"] div[data-testid="stContainer"],
        div[data-testid="stPopover"] div[data-testid="stElementContainer"],
        div[data-testid="stPopover"] div[data-testid="stElementContainer"] > div {
            background: #ffffff !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        div[data-testid="stPopover"] [data-testid="stVerticalBlock"] {
            align-items: stretch !important;
        }

        div[data-testid="stPopover"] [data-testid="stButton"] {
            width: 100% !important;
        }

        div[data-testid="stPopover"] [data-testid="stButton"] > button {
            justify-content: flex-start !important;
            text-align: left !important;
        }

        div[data-testid="stPopover"] [data-testid="stButton"] > button * {
            text-align: left !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] {
            width: 100% !important;
            margin: 0 !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-topic-filter-group-hook) [data-testid="stCheckbox"] {
            margin-left: 1rem !important;
            width: calc(100% - 1rem) !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-topic-filter-group-hook--single-subject) [data-testid="stCheckbox"] {
            margin-left: 0 !important;
            width: 100% !important;
        }

        .gm-topic-filter-group-title {
            color: #475569;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            margin: 0.3rem 0 0.12rem;
            text-transform: uppercase;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] label {
            align-items: center !important;
            cursor: pointer !important;
            gap: 0.55rem !important;
            justify-content: flex-start !important;
            padding: 0.1rem 0 !important;
            width: 100% !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] label > div:last-child,
        div[data-testid="stPopover"] [data-testid="stCheckbox"] [data-testid="stMarkdownContainer"] {
            flex: 0 1 auto !important;
            width: auto !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] [data-testid="stMarkdownContainer"] p {
            color: #0f172a !important;
            font-weight: 600 !important;
            margin: 0 !important;
            text-align: left !important;
        }

        div[data-testid="stPopover"] [data-testid="stCheckbox"] input {
            cursor: pointer !important;
        }

        div[data-testid="stPopover"] [data-testid="stHorizontalBlock"],
        div[data-testid="stPopover"] [data-testid="stHorizontalBlock"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        div[data-testid="stPopover"] div[data-testid="stButton"] button[kind="tertiary"] {
            background: #f8fbff !important;
            border: 1px solid #dbeafe !important;
            border-radius: 0.9rem !important;
            box-shadow: none !important;
            color: #1e3a8a !important;
            font-weight: 700 !important;
            justify-content: flex-start !important;
            min-height: 2.5rem !important;
            text-align: left !important;
        }

        div[data-testid="stPopover"] div[data-testid="stButton"] button[kind="tertiary"]:hover {
            background: #eef4ff !important;
            border-color: #bfdbfe !important;
        }

        div[data-testid="stSelectbox"] {
            cursor: pointer !important;
            margin-bottom: 0.2rem;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 999px !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06) !important;
            cursor: pointer !important;
            min-height: 2.55rem !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"],
        div[data-testid="stSelectbox"] [data-baseweb="select"] *,
        div[data-testid="stSelectbox"] [data-baseweb="select"] input {
            cursor: pointer !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] * {
            color: #0f172a !important;
        }

        div[data-baseweb="popover"],
        div[data-baseweb="popover"] [role="listbox"] {
            background: #ffffff !important;
            border: 1px solid #dbeafe !important;
            border-radius: 1rem !important;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12) !important;
            cursor: pointer !important;
        }

        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] li,
        div[data-baseweb="popover"] [role="option"] {
            background: #ffffff !important;
            cursor: pointer !important;
        }

        div[data-baseweb="popover"] *,
        div[data-baseweb="popover"] [role="option"] * {
            color: #0f172a !important;
        }

        div[data-baseweb="popover"] [role="option"]:hover {
            background: #f8fbff !important;
        }

        div[data-baseweb="popover"] [role="option"][aria-selected="true"] {
            background: #eef2ff !important;
        }

        div[data-testid="stForm"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stForm"] form {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            margin-top: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stForm"] form > div,
        div[data-testid="stForm"] [data-testid="stElementContainer"] {
            width: 100% !important;
        }

        div[data-testid="stForm"] form > div[data-testid="stVerticalBlock"] {
            gap: 0.55rem !important;
        }

        div[data-testid="stForm"] form > div[data-testid="stVerticalBlock"] > div {
            margin: 0 !important;
        }

        div[data-testid="stRadio"] {
            display: block !important;
            margin-left: auto !important;
            margin-right: auto !important;
            max-width: 100% !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] > label {
            color: #0f172a;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]),
        div[data-testid="stElementContainer"]:has(div[data-testid="stRadio"]) > div,
        div[data-testid="stRadio"] > div:first-of-type,
        div[data-testid="stRadio"] > div,
        div[data-testid="stRadio"] [role="radiogroup"] {
            width: 100% !important;
            max-width: none !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] {
            align-self: stretch !important;
            align-items: stretch !important;
            display: flex !important;
            flex-direction: column !important;
            gap: var(--gm-quiz-option-gap) !important;
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > * {
            align-self: stretch !important;
            display: block !important;
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] > * > * {
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            align-items: flex-start;
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1rem;
            box-sizing: border-box;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            cursor: pointer !important;
            column-gap: var(--gm-pending-choice-content-gap) !important;
            display: grid !important;
            grid-template-columns: 1rem minmax(0, 1fr);
            inline-size: 100% !important;
            justify-self: stretch !important;
            margin-bottom: 0 !important;
            max-width: none !important;
            min-width: 100% !important;
            padding: var(--gm-pending-choice-padding-block) var(--gm-pending-choice-padding-inline) !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] * {
            color: #0f172a !important;
            opacity: 1 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div {
            align-items: center !important;
            background: #eef4ff !important;
            border: 1.5px solid #bfd4ff !important;
            border-radius: 999px !important;
            box-shadow: none !important;
            color: #bfd4ff !important;
            display: inline-flex !important;
            flex: 0 0 auto !important;
            height: 1rem !important;
            justify-content: center !important;
            min-height: 1rem !important;
            min-width: 1rem !important;
            width: 1rem !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"],
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] > div,
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] p {
            max-width: none !important;
            width: 100% !important;
        }

        div[data-testid="stRadio"] input[type="radio"] {
            accent-color: #dbeafe !important;
            cursor: pointer !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child *,
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div * {
            fill: #eef4ff !important;
            color: #bfd4ff !important;
            stroke: #bfd4ff !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: #edf4ff;
            border-color: #93c5fd;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) input[type="radio"] {
            accent-color: #2563eb !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {
            background: #2563eb !important;
            border-color: #2563eb !important;
            color: #ffffff !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {
            color: #1d4ed8 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] svg,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child *,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div * {
            fill: #2563eb !important;
            color: #2563eb !important;
            stroke: #2563eb !important;
        }

        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stFormSubmitButton"] button {
            background: #edf4ff !important;
            border: 1px solid #93c5fd !important;
            color: #1d4ed8 !important;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.1) !important;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: #e2eeff !important;
            border-color: #60a5fa !important;
            color: #1d4ed8 !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stFormSubmitButton"] button {
            background: #edf4ff !important;
            border: 1px solid #93c5fd !important;
            color: #1d4ed8 !important;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.1) !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:first-child div[data-testid="stFormSubmitButton"] button:hover {
            background: #e2eeff !important;
            border-color: #60a5fa !important;
            color: #1d4ed8 !important;
        }

        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"],
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stFormSubmitButton"] button {
            background: #1e40af !important;
            border: 1px solid #1e3a8a !important;
            color: #ffffff !important;
            box-shadow: 0 12px 24px rgba(37, 99, 235, 0.22) !important;
        }

        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 1rem;
            cursor: pointer !important;
            font-weight: 700;
            min-height: 2.9rem;
        }

        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button[kind="secondary"],
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button [data-testid="baseButton-secondary"] {
            background: #fff4f4 !important;
            border: 1px solid #f5a3a3 !important;
            box-shadow: none !important;
            color: #b91c1c !important;
        }

        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button *,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button [data-testid="baseButton-secondary"] * {
            color: #b91c1c !important;
        }

        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button:hover,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button:active,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button [data-testid="baseButton-secondary"]:hover,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button [data-testid="baseButton-secondary"]:active {
            background: #fee2e2 !important;
            border-color: #f5a3a3 !important;
            box-shadow: none !important;
            color: #991b1b !important;
        }

        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button:focus,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button button:focus-visible,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button [data-testid="baseButton-secondary"]:focus,
        section[data-testid="stSidebar"] .st-key-gm_sidebar_logout_button [data-testid="baseButton-secondary"]:focus-visible {
            background: #fff4f4 !important;
            border-color: #f5a3a3 !important;
            box-shadow: 0 0 0 0.16rem rgba(245, 163, 163, 0.32) !important;
            color: #b91c1c !important;
            outline: none !important;
        }

        div[data-testid="stAlert"] {
            background: #ffffff !important;
            border: 1px solid #dbeafe !important;
            color: #0f172a !important;
        }

        div[data-testid="stAlert"] * {
            color: #0f172a !important;
        }
        </style>
        """
        ),
        unsafe_allow_html=True,
    )
