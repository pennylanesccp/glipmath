from __future__ import annotations

from datetime import date, timedelta
from html import escape
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

from app.state.session_state import (
    QUESTION_SELECTION_KEY,
    clear_current_question,
    clear_question_skip,
    get_current_alternatives,
    get_current_question_id,
    get_last_answer_result,
    get_question_started_at,
    get_session_id,
    get_skipped_question_ids,
    get_theme_mode,
    initialize_session_state,
    is_current_question_answered,
    is_submission_in_progress,
    mark_question_answered,
    mark_question_skipped,
    set_current_question,
    set_theme_mode,
    start_submission,
    finish_submission,
)
from app.ui.template_renderer import asset_to_data_uri, render_template
from modules.auth.auth_service import trigger_logout
from modules.config.settings import AppSettings
from modules.domain.models import AnswerAttempt, DisplayAlternative, Question, User
from modules.services.answer_service import AnswerService
from modules.services.question_service import (
    build_display_alternatives,
    find_display_alternative,
    find_question_by_id,
    select_next_question,
)
from modules.storage.bigquery_client import BigQueryError
from modules.utils.datetime_utils import utc_now


# Ajusta só estas duas linhas se você mudou os ícones de lugar.
FIRE_ICON_RELATIVE_PATH = "assets/status/fire-svgrepo-com.svg"
PODIUM_ICON_RELATIVE_PATH = "assets/status/pedestal-podium-svgrepo-com.svg"


def render_main_page(
    *,
    settings: AppSettings,
    user: User,
    questions: list[Question],
    answers: list[AnswerAttempt],
    answer_service: AnswerService,
    leaderboard_frame: pd.DataFrame | None = None,
) -> None:
    initialize_session_state()

    theme_mode = get_theme_mode()
    subject_slug = _get_query_value("subject") or "todas"

    filtered_questions, subject_items = _filter_questions_by_subject(
        questions=questions,
        selected_subject_slug=subject_slug,
    )

    current_question, alternatives = _ensure_current_question(filtered_questions, answers)

    _consume_page_actions(
        user=user,
        current_question=current_question,
        alternatives=alternatives,
        answer_service=answer_service,
        subject_slug=subject_slug,
        theme_mode=theme_mode,
    )

    current_question, alternatives = _ensure_current_question(filtered_questions, answers)

    if current_question is None:
        st.markdown(
            render_template(
                "pages/question_session.html",
                {
                    "THEME_NAME": theme_mode,
                    "THEME_TOGGLE_HREF": _build_href(
                        theme=("light" if theme_mode == "dark" else "dark"),
                        subject=subject_slug,
                    ),
                    "THEME_TOGGLE_CLASS": (
                        "gm-theme-toggle--dark" if theme_mode == "dark" else "gm-theme-toggle--light"
                    ),
                    "CURRENT_SUBJECT_LABEL": _subject_label_from_items(subject_items, subject_slug),
                    "SUBJECT_OPTIONS_HTML": _render_subject_options_html(
                        subject_items=subject_items,
                        selected_subject_slug=subject_slug,
                        theme_mode=theme_mode,
                    ),
                    "FIRE_ICON_DATA_URI": _load_icon_or_fallback(FIRE_ICON_RELATIVE_PATH, "fire"),
                    "PODIUM_ICON_DATA_URI": _load_icon_or_fallback(PODIUM_ICON_RELATIVE_PATH, "podium"),
                    "STREAK_TEXT": _format_day_streak(_compute_day_streak(answers)),
                    "RANK_TEXT": _resolve_rank_text(leaderboard_frame, user.email),
                    "TIMER_IFRAME_SRCDOC": _build_timer_srcdoc(
                        elapsed_seconds=0,
                        theme_mode=theme_mode,
                        is_running=False,
                    ),
                    "LOGOUT_HREF": _build_href(
                        theme=theme_mode,
                        subject=subject_slug,
                        action="logout",
                    ),
                    "QUESTION_STATEMENT_HTML": "Nenhuma questão disponível para esse filtro agora.",
                    "ALTERNATIVES_HTML": '<div class="gm-info-card">Troca a disciplina acima ou carrega mais questões.</div>',
                    "BOTTOM_ACTION_HTML": "",
                },
            ),
            unsafe_allow_html=True,
        )
        return

    question_answered = is_current_question_answered()
    last_result = get_last_answer_result()

    selected_option_id = _selected_option_id_for_render(current_question.id_question)
    elapsed_seconds = _resolve_elapsed_seconds(question_answered=question_answered, last_result=last_result)

    page_html = render_template(
        "pages/question_session.html",
        {
            "THEME_NAME": theme_mode,
            "THEME_TOGGLE_HREF": _build_href(
                theme=("light" if theme_mode == "dark" else "dark"),
                subject=subject_slug,
            ),
            "THEME_TOGGLE_CLASS": (
                "gm-theme-toggle--dark" if theme_mode == "dark" else "gm-theme-toggle--light"
            ),
            "CURRENT_SUBJECT_LABEL": _subject_label_from_items(subject_items, subject_slug),
            "SUBJECT_OPTIONS_HTML": _render_subject_options_html(
                subject_items=subject_items,
                selected_subject_slug=subject_slug,
                theme_mode=theme_mode,
            ),
            "FIRE_ICON_DATA_URI": _load_icon_or_fallback(FIRE_ICON_RELATIVE_PATH, "fire"),
            "PODIUM_ICON_DATA_URI": _load_icon_or_fallback(PODIUM_ICON_RELATIVE_PATH, "podium"),
            "STREAK_TEXT": _format_day_streak(_compute_day_streak(answers)),
            "RANK_TEXT": _resolve_rank_text(leaderboard_frame, user.email),
            "TIMER_IFRAME_SRCDOC": _build_timer_srcdoc(
                elapsed_seconds=elapsed_seconds,
                theme_mode=theme_mode,
                is_running=not question_answered,
            ),
            "LOGOUT_HREF": _build_href(
                theme=theme_mode,
                subject=subject_slug,
                action="logout",
            ),
            "QUESTION_STATEMENT_HTML": _text_to_html(current_question.statement),
            "ALTERNATIVES_HTML": _render_alternatives_html(
                alternatives=alternatives,
                selected_option_id=selected_option_id,
                question_answered=question_answered,
                subject_slug=subject_slug,
                theme_mode=theme_mode,
            ),
            "BOTTOM_ACTION_HTML": _render_bottom_action_html(
                question_answered=question_answered,
                selected_option_id=selected_option_id,
                is_correct=bool(last_result.get("is_correct")) if last_result else False,
                subject_slug=subject_slug,
                theme_mode=theme_mode,
            ),
        },
    )

    st.markdown(page_html, unsafe_allow_html=True)


def _consume_page_actions(
    *,
    user: User,
    current_question: Question | None,
    alternatives: list[DisplayAlternative],
    answer_service: AnswerService,
    subject_slug: str,
    theme_mode: str,
) -> None:
    requested_theme = _get_query_value("theme")
    if requested_theme:
        normalized_requested_theme = "light" if requested_theme == "light" else "dark"
        if normalized_requested_theme != theme_mode:
            set_theme_mode(normalized_requested_theme)
            _reset_page_query_params(
                theme=normalized_requested_theme,
                subject=subject_slug,
            )
            st.rerun()

    selected_option_id = _get_query_value("select")
    if selected_option_id and current_question is not None and not is_current_question_answered():
        st.session_state[QUESTION_SELECTION_KEY] = selected_option_id
        _reset_page_query_params(
            theme=get_theme_mode(),
            subject=subject_slug,
        )
        st.rerun()

    action = (_get_query_value("action") or "").strip().lower()
    if not action:
        return

    if action == "logout":
        trigger_logout()
        st.stop()

    if current_question is None:
        _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
        st.rerun()

    if action == "skip" and not is_current_question_answered():
        mark_question_skipped(current_question.id_question)
        clear_current_question()
        _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
        st.rerun()

    if action == "next" and is_current_question_answered():
        clear_current_question()
        _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
        st.rerun()

    if action != "submit" or is_current_question_answered():
        _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
        st.rerun()

    chosen_option_id = str(st.session_state.get(QUESTION_SELECTION_KEY) or "").strip()
    selected_alternative = find_display_alternative(alternatives, chosen_option_id)
    if selected_alternative is None:
        _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
        st.rerun()

    if is_submission_in_progress():
        _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
        st.rerun()

    start_submission()
    started_at = get_question_started_at() or utc_now()
    elapsed_seconds = max((utc_now() - started_at).total_seconds(), 0.0)

    try:
        evaluation = answer_service.submit_answer(
            user=user,
            question=current_question,
            selected_alternative=selected_alternative,
            session_id=get_session_id(),
            time_spent_seconds=elapsed_seconds,
        )
    except (BigQueryError, ValueError):
        finish_submission()
        raise

    clear_question_skip(current_question.id_question)
    mark_question_answered(evaluation, selected_option_id=selected_alternative.option_id)
    _reset_page_query_params(theme=get_theme_mode(), subject=subject_slug)
    st.rerun()


def _ensure_current_question(
    questions: list[Question],
    answers: list[AnswerAttempt],
) -> tuple[Question | None, list[DisplayAlternative]]:
    current_question = find_question_by_id(questions, get_current_question_id())
    current_alternatives = get_current_alternatives()

    if current_question is not None and current_alternatives:
        return current_question, current_alternatives

    answered_question_ids = {answer.id_question for answer in answers}
    skipped_question_ids = get_skipped_question_ids()
    next_question = select_next_question(
        questions,
        answered_question_ids | skipped_question_ids,
    )

    if next_question is None:
        return None, []

    alternatives = build_display_alternatives(next_question)
    set_current_question(next_question.id_question, alternatives)
    return next_question, alternatives


def _filter_questions_by_subject(
    *,
    questions: list[Question],
    selected_subject_slug: str,
) -> tuple[list[Question], list[tuple[str, str]]]:
    labels_by_slug: dict[str, str] = {"todas": "Todas"}

    for question in questions:
        label = (question.subject or "").strip()
        if not label:
            continue
        slug = _slugify_subject(label)
        labels_by_slug.setdefault(slug, label)

    subject_items = [("todas", "Todas"), *sorted(
        [(slug, label) for slug, label in labels_by_slug.items() if slug != "todas"],
        key=lambda item: item[1].lower(),
    )]

    valid_slugs = {slug for slug, _ in subject_items}
    normalized_subject_slug = selected_subject_slug if selected_subject_slug in valid_slugs else "todas"

    if normalized_subject_slug == "todas":
        return questions, subject_items

    filtered = [
        question
        for question in questions
        if _slugify_subject(question.subject or "") == normalized_subject_slug
    ]
    return filtered, subject_items


def _render_subject_options_html(
    *,
    subject_items: list[tuple[str, str]],
    selected_subject_slug: str,
    theme_mode: str,
) -> str:
    rows: list[str] = []

    for slug, label in subject_items:
        classes = "gm-subject-option"
        if slug == selected_subject_slug:
            classes += " is-active"

        rows.append(
            (
                f'<a href="{escape(_build_href(theme=theme_mode, subject=slug), quote=True)}" '
                f'class="{classes}" target="_self" rel="noopener noreferrer">{escape(label)}</a>'
            )
        )

    return "".join(rows)


def _render_alternatives_html(
    *,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    question_answered: bool,
    subject_slug: str,
    theme_mode: str,
) -> str:
    rows: list[str] = []

    for alternative in alternatives:
        explanation_html = ""
        if question_answered and alternative.explanation:
            explanation_html = (
                f'<p class="gm-option-explanation">{_text_to_html(alternative.explanation)}</p>'
            )

        if question_answered:
            option_class = "gm-option"
            if alternative.is_correct:
                option_class += " gm-option--correct"
            elif alternative.option_id == selected_option_id:
                option_class += " gm-option--wrong-selected"
            else:
                option_class += " gm-option--wrong"

            rows.append(
                f"""
                <div class="{option_class}">
                    <span class="gm-option-radio"></span>
                    <span class="gm-option-content">
                        <span class="gm-option-text">{escape(alternative.alternative_text)}</span>
                        {explanation_html}
                    </span>
                </div>
                """
            )
            continue

        option_class = "gm-option"
        if alternative.option_id == selected_option_id:
            option_class += " gm-option--selected"

        option_href = _build_href(
            theme=theme_mode,
            subject=subject_slug,
            select=alternative.option_id,
        )

        rows.append(
            f"""
            <a
                href="{escape(option_href, quote=True)}"
                class="{option_class}"
                target="_self"
                rel="noopener noreferrer"
            >
                <span class="gm-option-radio"></span>
                <span class="gm-option-content">
                    <span class="gm-option-text">{escape(alternative.alternative_text)}</span>
                </span>
            </a>
            """
        )

    return "".join(rows)


def _render_bottom_action_html(
    *,
    question_answered: bool,
    selected_option_id: str | None,
    is_correct: bool,
    subject_slug: str,
    theme_mode: str,
) -> str:
    if question_answered:
        result_class = "gm-result-card gm-result-card--correct" if is_correct else "gm-result-card"
        result_text = "Você acertou" if is_correct else "Você errou"

        return f"""
        <div class="gm-bottom-action">
            <div class="gm-bottom-action-row">
                <div class="{result_class}">{result_text}</div>
                <a
                    href="{escape(_build_href(theme=theme_mode, subject=subject_slug, action='next'), quote=True)}"
                    class="gm-link-button gm-link-button--primary"
                    target="_self"
                    rel="noopener noreferrer"
                >
                    Próxima questão
                </a>
            </div>
        </div>
        """

    verify_href = "#"
    verify_class = "gm-link-button gm-link-button--primary is-disabled"

    if selected_option_id:
        verify_href = _build_href(theme=theme_mode, subject=subject_slug, action="submit")
        verify_class = "gm-link-button gm-link-button--primary"

    return f"""
    <div class="gm-bottom-action">
        <div class="gm-bottom-action-row">
            <a
                href="{escape(_build_href(theme=theme_mode, subject=subject_slug, action='skip'), quote=True)}"
                class="gm-link-button gm-link-button--skip"
                target="_self"
                rel="noopener noreferrer"
            >
                Pular questão
            </a>
            <a
                href="{escape(verify_href, quote=True)}"
                class="{verify_class}"
                target="_self"
                rel="noopener noreferrer"
            >
                Verificar resposta
            </a>
        </div>
    </div>
    """


def _build_timer_srcdoc(
    *,
    elapsed_seconds: int,
    theme_mode: str,
    is_running: bool,
) -> str:
    background = "#eff6ff" if theme_mode == "light" else "rgba(59,130,246,0.14)"
    border = "#bfdbfe" if theme_mode == "light" else "rgba(96,165,250,0.30)"
    text_color = "#2563eb" if theme_mode == "light" else "#93c5fd"

    return f"""
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
                background: {background};
                border: 1px solid {border};
                border-radius: 999px;
                box-sizing: border-box;
                color: {text_color};
                display: inline-flex;
                font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                font-size: 13px;
                font-weight: 800;
                gap: 8px;
                height: 36px;
                justify-content: center;
                min-width: 108px;
                padding: 0 12px;
                white-space: nowrap;
                width: 108px;
            }}

            .gm-timer-icon {{
                display: block;
                flex: 0 0 auto;
                height: 16px;
                width: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="gm-timer-chip">
            <svg class="gm-timer-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 8V12L14.8 14.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M9 3H15" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"></path>
                <path d="M12 5C7.58 5 4 8.58 4 13C4 17.42 7.58 21 12 21C16.42 21 20 17.42 20 13C20 8.58 16.42 5 12 5Z" stroke="currentColor" stroke-width="2.1"></path>
            </svg>
            <span id="gm-timer-value"></span>
        </div>
        <script>
            const timerElement = document.getElementById("gm-timer-value");
            let elapsed = {max(int(elapsed_seconds), 0)};
            const isRunning = {str(is_running).lower()};

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

            if (isRunning) {{
                window.setInterval(() => {{
                    elapsed += 1;
                    timerElement.textContent = formatElapsed(elapsed);
                }}, 1000);
            }}
        </script>
    </body>
    </html>
    """.strip()


def _resolve_elapsed_seconds(
    *,
    question_answered: bool,
    last_result: dict[str, object] | None,
) -> int:
    if question_answered and last_result:
        try:
            return max(int(round(float(last_result.get("time_spent_seconds", 0) or 0))), 0)
        except (TypeError, ValueError):
            return 0

    started_at = get_question_started_at()
    if started_at is None:
        return 0

    return max(int((utc_now() - started_at).total_seconds()), 0)


def _selected_option_id_for_render(current_question_id: int) -> str | None:
    if is_current_question_answered():
        last_result = get_last_answer_result()
        if last_result and int(last_result.get("id_question", -1)) == current_question_id:
            selected = str(last_result.get("selected_option_id") or "").strip()
            return selected or None

    selected = str(st.session_state.get(QUESTION_SELECTION_KEY) or "").strip()
    return selected or None


def _load_icon_or_fallback(relative_path: str, icon_name: str) -> str:
    try:
        return asset_to_data_uri(relative_path)
    except FileNotFoundError:
        if icon_name == "fire":
            return (
                "data:image/svg+xml;utf8,"
                "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23f97316'>"
                "<path d='M13.5 2s.5 3-1.5 5-3 3-3 6a5 5 0 0010 0c0-3-2-4.5-3.2-5.8C14.2 5.6 13.5 2 13.5 2z'/>"
                "</svg>"
            )
        return (
            "data:image/svg+xml;utf8,"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23eab308'>"
            "<path d='M7 4h10v3h2v3c0 2.2-1.8 4-4 4h-1.1A5 5 0 0113 17.9V20h4v2H7v-2h4v-2.1A5 5 0 019.1 14H8c-2.2 0-4-1.8-4-4V7h2V4zm-1 5v1a2 2 0 002 2h.3A5 5 0 018 11V9H6zm12 0h-2v2a5 5 0 01-.3 1H16a2 2 0 002-2V9z'/>"
            "</svg>"
        )


def _resolve_rank_text(leaderboard_frame: pd.DataFrame | None, user_email: str) -> str:
    if leaderboard_frame is None or leaderboard_frame.empty:
        return "#—"

    frame = leaderboard_frame.copy()
    if "user_email" not in frame.columns or "rank" not in frame.columns:
        return "#—"

    frame["normalized_user_email"] = frame["user_email"].astype(str).str.strip().str.lower()
    match = frame.loc[frame["normalized_user_email"] == user_email.strip().lower()]

    if match.empty:
        return "#—"

    rank_value = match.iloc[0]["rank"]
    try:
        return f"#{int(rank_value)}"
    except (TypeError, ValueError):
        return "#—"


def _compute_day_streak(answers: list[AnswerAttempt]) -> int:
    if not answers:
        return 0

    answered_days = {
        (answer.answered_at_local.date() if answer.answered_at_local else answer.answered_at_utc.date())
        for answer in answers
    }

    today = date.today()
    streak = 0
    current_day = today

    while current_day in answered_days:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


def _format_day_streak(streak: int) -> str:
    if streak <= 0:
        return "0d"
    if streak == 1:
        return "1d"
    return f"{streak}d"


def _subject_label_from_items(subject_items: list[tuple[str, str]], subject_slug: str) -> str:
    for slug, label in subject_items:
        if slug == subject_slug:
            return label
    return "Todas"


def _slugify_subject(subject: str) -> str:
    text = str(subject).strip().lower()
    if not text:
        return "todas"
    return "-".join(text.split())


def _text_to_html(text: str | None) -> str:
    safe = escape(str(text or "").strip())
    return safe.replace("\n", "<br>")


def _build_href(
    *,
    theme: str,
    subject: str,
    action: str | None = None,
    select: str | None = None,
) -> str:
    params: dict[str, str] = {
        "theme": "light" if theme == "light" else "dark",
        "subject": subject or "todas",
    }

    if action:
        params["action"] = action

    if select:
        params["select"] = select

    return f"?{urlencode(params)}"


def _reset_page_query_params(*, theme: str, subject: str) -> None:
    st.query_params.clear()
    st.query_params["theme"] = "light" if theme == "light" else "dark"
    st.query_params["subject"] = subject or "todas"


def _get_query_value(key: str) -> str | None:
    raw_value = st.query_params.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        return str(raw_value[0]).strip() if raw_value else None
    return str(raw_value).strip()