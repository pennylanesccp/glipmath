from __future__ import annotations

import streamlit as st

from app.state.session_state import (
    clear_current_question,
    get_current_professor_tool,
    get_current_student_view,
    get_current_workspace,
    get_project_filter,
    set_current_professor_tool,
    set_current_student_view,
    set_current_workspace,
    set_project_filter,
    set_subject_filters,
    set_topic_filters,
)
from modules.auth.auth_service import trigger_logout
from modules.domain.models import User
from modules.services.question_service import format_project_label


def render_sidebar_ui(
    *,
    user: User,
    project_options: list[str],
    selected_project: str | None,
) -> tuple[str | None, str]:
    """Apply sidebar styles and render authenticated navigation controls."""

    _apply_workspace_shell_styles()
    return _render_authenticated_shell_sidebar(
        user=user,
        project_options=project_options,
        selected_project=selected_project,
    )


def render_sidebar_logout_button() -> None:
    with st.sidebar:
        with st.container():
            st.html('<div class="gm-sidebar-section-hook gm-sidebar-logout-button-hook"></div>')
            st.html('<div class="gm-sidebar-separator gm-sidebar-logout-separator-hook"></div>')
            if st.button(
                "Sair",
                key="gm_sidebar_logout_button",
                type="secondary",
                use_container_width=True,
            ):
                trigger_logout()


def _render_authenticated_shell_sidebar(
    *,
    user: User,
    project_options: list[str],
    selected_project: str | None,
) -> tuple[str | None, str]:
    project_choice = selected_project
    current_workspace = "student"

    with st.sidebar:
        if len(project_options) > 1:
            with st.container():
                st.html('<div class="gm-sidebar-section-hook gm-sidebar-project-section-hook"></div>')
                st.caption("PROJETO")
                project_choice = st.selectbox(
                    "Projeto",
                    options=project_options,
                    index=project_options.index(selected_project) if selected_project in project_options else 0,
                    format_func=_format_project_option_label,
                    key="gm_global_project_filter_select",
                    label_visibility="collapsed",
                )

        if user.can_access_professor_space:
            with st.container():
                st.html('<div class="gm-sidebar-section-hook gm-sidebar-workspace-section-hook"></div>')
                st.caption("ESPA\u00c7O")
                current_workspace = get_current_workspace()
                st.html('<div class="gm-sidebar-workspace-control-hook"></div>')
                workspace_choice = _render_workspace_button_group(current_workspace)
            normalized_workspace = workspace_choice if workspace_choice in {"student", "professor"} else "student"
            if normalized_workspace != current_workspace:
                set_current_workspace(normalized_workspace)
                clear_current_question()
                st.rerun()
            current_workspace = normalized_workspace
        else:
            if get_current_workspace() != "student":
                set_current_workspace("student")
            if get_current_professor_tool() is not None:
                set_current_professor_tool(None)

        if current_workspace == "student":
            with st.container():
                st.html('<div class="gm-sidebar-section-hook gm-sidebar-view-section-hook"></div>')
                st.caption("VIS\u00c3O")
                current_student_view = get_current_student_view()
                student_view_choice = st.segmented_control(
                    "Vis\u00e3o do aluno",
                    options=["practice", "stats"],
                    default=current_student_view,
                    format_func=_format_student_view_label,
                    key="gm_student_view_segmented_control",
                    label_visibility="collapsed",
                    width="stretch",
                )
            normalized_student_view = (
                student_view_choice if student_view_choice in {"practice", "stats"} else "practice"
            )
            if normalized_student_view != current_student_view:
                set_current_student_view(normalized_student_view)
                if normalized_student_view == "practice":
                    clear_current_question()
                st.rerun()

    if project_choice != get_project_filter():
        st.session_state.pop("gm_subject_filter_select", None)
        set_project_filter(project_choice)
        set_subject_filters(())
        set_topic_filters(())
        clear_current_question()
        st.rerun()

    return project_choice, current_workspace


def _render_workspace_button_group(current_workspace: str) -> str:
    workspace_choice = st.segmented_control(
        "Espa\u00e7o",
        options=["student", "professor"],
        default=current_workspace,
        format_func=_format_workspace_label,
        key="gm_workspace_segmented_control",
        label_visibility="collapsed",
        width="stretch",
    )
    return workspace_choice if workspace_choice in {"student", "professor"} else current_workspace


def _format_project_option_label(project_key: str) -> str:
    return format_project_label(project_key)


def _format_student_view_label(view_name: str) -> str:
    return "Estat\u00edsticas" if view_name == "stats" else "Quest\u00f5es"


def _format_workspace_label(workspace_name: str) -> str:
    return "Professor" if workspace_name == "professor" else "Aluno"


def _apply_workspace_shell_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --gm-sidebar-section-gap: 0.24rem;
            --gm-sidebar-section-margin-bottom: 16px;
            --gm-sidebar-horizontal-padding: 1.25rem;
            --gm-sidebar-caption-margin-top: 0;
            --gm-sidebar-caption-margin-bottom: 0.24rem;
            --gm-sidebar-actions-padding-top: 0.45rem;
        }

        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
            padding-left: var(--gm-sidebar-horizontal-padding) !important;
            padding-right: var(--gm-sidebar-horizontal-padding) !important;
        }

        div[data-testid="stSelectbox"] label p,
        div[data-testid="stSelectbox"] label span {
            color: #334155 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stSelectbox"] {
            cursor: pointer !important;
            margin-bottom: 0;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 0.78rem !important;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05) !important;
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

        div[data-testid="stSegmentedControl"] {
            margin: 0;
            width: 100% !important;
            max-width: 100% !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] {
            margin: var(--gm-sidebar-caption-margin-top) 0 var(--gm-sidebar-caption-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] p {
            color: #94a3b8 !important;
            font-size: 0.64rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.16em !important;
            line-height: 1.1 !important;
            text-transform: uppercase !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-section-hook) {
            gap: var(--gm-sidebar-section-gap) !important;
            margin-bottom: var(--gm-sidebar-section-margin-bottom) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.gm-sidebar-logout-button-hook) {
            gap: 0.44rem !important;
            margin-bottom: 0 !important;
            padding-top: var(--gm-sidebar-actions-padding-top) !important;
        }

        section[data-testid="stSidebar"] .gm-sidebar-separator {
            background: #dbeafe;
            height: 1px;
            margin: 0.16rem 0 0.72rem;
            width: 100%;
        }

        section[data-testid="stSidebar"] .gm-sidebar-logout-separator-hook {
            margin-top: 0.08rem;
            margin-bottom: 0.78rem;
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

        div[data-testid="stSegmentedControl"] > div {
            width: 100% !important;
            max-width: 100% !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [data-baseweb="button-group"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radiogroup"] {
            display: flex !important;
            justify-content: stretch !important;
            align-items: center !important;
            gap: 0.18rem !important;
            width: 100% !important;
            max-width: 100% !important;
            padding: 0.18rem !important;
            margin: 0 !important;
            background: #f1f5f9 !important;
            border: 1px solid #dbe5f1 !important;
            border-radius: 0.78rem !important;
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] > div,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radiogroup"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[kind="primary"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[kind="secondary"] {
            position: relative !important;
            flex: 1 1 0 !important;
            min-height: auto !important;
            padding: 0.42rem 0.4rem !important;
            margin: 0 !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 0.6rem !important;
            box-shadow: none !important;
            color: #64748b !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            justify-content: center !important;
            line-height: 1.15 !important;
            text-align: center !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"] p,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button p {
            color: inherit !important;
            font-size: inherit !important;
            line-height: inherit !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button:hover {
            color: #334155 !important;
            background: rgba(255, 255, 255, 0.64) !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"][aria-selected="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radio"][aria-pressed="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-checked="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-selected="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[kind="primary"] {
            color: #0f172a !important;
            background: #ffffff !important;
            border-color: #dbe5f1 !important;
            box-shadow: 0 3px 8px rgba(15, 23, 42, 0.08) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
