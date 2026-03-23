from __future__ import annotations

from html import escape
from urllib.parse import urlencode

from app.ui.template_renderer import asset_to_data_uri, raw_html, render_template
from modules.domain.models import DisplayAlternative

FIRE_ICON_RELATIVE_PATH = "assets/icons/fire-svgrepo-com.svg"
PODIUM_ICON_RELATIVE_PATH = "assets/icons/pedestal-podium-svgrepo-com.svg"


def render_question_session_template(
    *,
    selected_subject: str,
    subject_options: list[str],
    streak_text: str,
    rank_text: str,
    timer_elapsed_seconds: int,
    timer_running: bool,
    logout_href: str,
    question_statement_html: str,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    question_answered: bool,
    answer_is_correct: bool,
    empty_state_html: str | None = None,
) -> str:
    """Render the authenticated question/session page from one HTML template."""

    subject_filter = selected_subject if selected_subject in subject_options else "Todas"
    alternatives_html = empty_state_html or _render_alternatives_html(
        alternatives=alternatives,
        selected_option_id=selected_option_id,
        question_answered=question_answered,
        answer_is_correct=answer_is_correct,
        subject_filter=subject_filter,
    )
    bottom_action_html = "" if empty_state_html else _render_bottom_action_html(
        question_answered=question_answered,
        selected_option_id=selected_option_id,
        answer_is_correct=answer_is_correct,
        subject_filter=subject_filter,
    )

    return render_template(
        "pages/question_session.html",
        {
            "CURRENT_SUBJECT_LABEL": subject_filter,
            "SUBJECT_OPTIONS_HTML": raw_html(
                _render_subject_options_html(
                    subject_options=subject_options,
                    selected_subject=subject_filter,
                )
            ),
            "FIRE_ICON_DATA_URI": _load_icon_or_fallback(FIRE_ICON_RELATIVE_PATH, "fire"),
            "PODIUM_ICON_DATA_URI": _load_icon_or_fallback(PODIUM_ICON_RELATIVE_PATH, "podium"),
            "STREAK_TEXT": streak_text,
            "RANK_TEXT": rank_text,
            "TIMER_HTML": raw_html(
                _build_timer_html(
                    elapsed_seconds=timer_elapsed_seconds,
                    is_running=timer_running,
                )
            ),
            "LOGOUT_HREF": logout_href,
            "QUESTION_STATEMENT_HTML": raw_html(question_statement_html),
            "ALTERNATIVES_HTML": raw_html(alternatives_html),
            "BOTTOM_ACTION_HTML": raw_html(bottom_action_html),
        },
    )


def build_page_href(
    *,
    subject: str,
    action: str | None = None,
    select: str | None = None,
) -> str:
    """Build in-app links preserving stable session-page state."""

    params: dict[str, str] = {
        "subject": normalize_subject_filter(subject),
    }
    if action:
        params["action"] = action
    if select:
        params["select"] = select
    return f"?{urlencode(params)}"


def normalize_subject_filter(subject: str | None) -> str:
    """Normalize blank subject filters to the canonical all-subject label."""

    text = str(subject or "").strip()
    return text or "Todas"


def format_elapsed_time(total_seconds: float | int) -> str:
    """Format elapsed seconds as mm:ss or h:mm:ss."""

    safe_seconds = max(int(float(total_seconds or 0)), 0)
    seconds = safe_seconds % 60
    total_minutes = safe_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def text_to_html(text: str | None) -> str:
    """Render plain multi-line text as safe HTML."""

    return escape(str(text or "").strip()).replace("\n", "<br>")


def _render_subject_options_html(
    *,
    subject_options: list[str],
    selected_subject: str,
) -> str:
    rows: list[str] = []
    for subject in subject_options:
        option_class = "gm-subject-option"
        if subject == selected_subject:
            option_class += " is-active"
        rows.append(
            (
                f'<a href="{escape(build_page_href(subject=subject), quote=True)}" '
                f'class="{option_class}" target="_self" rel="noopener noreferrer">{escape(subject)}</a>'
            )
        )
    return "".join(rows)


def _render_alternatives_html(
    *,
    alternatives: list[DisplayAlternative],
    selected_option_id: str | None,
    question_answered: bool,
    answer_is_correct: bool,
    subject_filter: str,
) -> str:
    rows: list[str] = []
    for alternative in alternatives:
        explanation_html = ""
        if question_answered and alternative.explanation:
            explanation_html = (
                f'<p class="gm-option-explanation">{text_to_html(alternative.explanation)}</p>'
            )

        option_class = _resolve_option_class(
            alternative=alternative,
            selected_option_id=selected_option_id,
            question_answered=question_answered,
            answer_is_correct=answer_is_correct,
        )
        option_body = (
            '<span class="gm-option-radio"></span>'
            '<span class="gm-option-content">'
            f'<span class="gm-option-text">{escape(alternative.alternative_text)}</span>'
            f"{explanation_html}"
            "</span>"
        )

        if question_answered:
            rows.append(f'<div class="{option_class}">{option_body}</div>')
            continue

        rows.append(
            (
                f'<a href="{escape(build_page_href(subject=subject_filter, select=alternative.option_id), quote=True)}" '
                f'class="{option_class}" target="_self" rel="noopener noreferrer">{option_body}</a>'
            )
        )

    return "".join(rows)


def _render_bottom_action_html(
    *,
    question_answered: bool,
    selected_option_id: str | None,
    answer_is_correct: bool,
    subject_filter: str,
) -> str:
    if question_answered:
        result_class = "gm-result-card gm-result-card--correct" if answer_is_correct else "gm-result-card"
        result_text = "Voce acertou" if answer_is_correct else "Voce errou"
        return (
            '<div class="gm-bottom-action">'
            '<div class="gm-bottom-action-row">'
            f'<div class="{result_class}">{result_text}</div>'
            f'<a href="{escape(build_page_href(subject=subject_filter, action="next"), quote=True)}" '
            'class="gm-link-button gm-link-button--primary" target="_self" rel="noopener noreferrer">'
            "Proxima questao"
            "</a>"
            "</div>"
            "</div>"
        )

    verify_href = "#"
    verify_class = "gm-link-button gm-link-button--primary is-disabled"
    if selected_option_id:
        verify_href = build_page_href(subject=subject_filter, action="submit")
        verify_class = "gm-link-button gm-link-button--primary"

    return (
        '<div class="gm-bottom-action">'
        '<div class="gm-bottom-action-row">'
        f'<a href="{escape(build_page_href(subject=subject_filter, action="skip"), quote=True)}" '
        'class="gm-link-button gm-link-button--skip" target="_self" rel="noopener noreferrer">'
        "Pular questao"
        "</a>"
        f'<a href="{escape(verify_href, quote=True)}" class="{verify_class}" '
        'target="_self" rel="noopener noreferrer">'
        "Verificar resposta"
        "</a>"
        "</div>"
        "</div>"
    )


def _resolve_option_class(
    *,
    alternative: DisplayAlternative,
    selected_option_id: str | None,
    question_answered: bool,
    answer_is_correct: bool,
) -> str:
    if not question_answered:
        return "gm-option gm-option--selected" if alternative.option_id == selected_option_id else "gm-option"
    if alternative.is_correct:
        return "gm-option gm-option--correct"
    if not answer_is_correct and alternative.option_id == selected_option_id:
        return "gm-option gm-option--wrong-selected"
    return "gm-option gm-option--neutral"


def _build_timer_html(
    *,
    elapsed_seconds: int,
    is_running: bool,
) -> str:
    initial_text = format_elapsed_time(elapsed_seconds)
    pulse_html = ""
    if is_running:
        pulse_html = '<span class="gm-inline-timer-pulse" aria-hidden="true"></span>'

    return (
        '<div class="gm-inline-timer-chip" aria-label="Cronometro">'
        f"{pulse_html}"
        '<svg class="gm-inline-timer-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M12 8V12L14.8 14.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"></path>'
        '<path d="M9 3H15" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"></path>'
        '<path d="M12 5C7.58 5 4 8.58 4 13C4 17.42 7.58 21 12 21C16.42 21 20 17.42 20 13C20 8.58 16.42 5 12 5Z" stroke="currentColor" stroke-width="2.1"></path>'
        "</svg>"
        f'<span class="gm-inline-timer-value">{initial_text}</span>'
        "</div>"
    )


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
