from __future__ import annotations

from html import escape
from html.parser import HTMLParser
import re

from app.ui.markdown_renderer import markdown_to_html, markdown_to_plain_text
from modules.domain.models import DisplayAlternative

DAY_STREAK_DESCRIPTION = "Dias seguidos com atividade."
QUESTION_STREAK_DESCRIPTION = "Sequência atual de respostas corretas."
RANK_DESCRIPTION = "Sua posição atual no ranking."
TIMER_DESCRIPTION = "Tempo gasto na questão atual."
FENCED_CODE_BLOCK_PATTERN = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)
QUESTION_BOARD_CONTROL_LABELS = frozenset({"show", "hint"})
QUESTION_BOARD_MOVE_INSTRUCTION_PATTERN = re.compile(
    (
        r"(?is)\bMove\s+the\s+"
        r"(?:king|queen|rook|bishop|knight|pawn)"
        r"\s+on\s+(?P<square>[a-h][1-8])\.?"
        r"(?:\s|<br\s*/?>)*"
    )
)
QUESTION_BOARD_STATUS_BLOCK_PATTERN = re.compile(
    (
        r"(?is)"
        r"(?:<p>\s*Generated\s+\d+\s+puzzles?\s+from\s+\d+\s+games?\.?(?:\s|<br\s*/?>)*</p>"
        r"|<div(?:\s[^>]*)?>\s*Generated\s+\d+\s+puzzles?\s+from\s+\d+\s+games?\.?(?:\s|<br\s*/?>)*</div>"
        r"|<span(?:\s[^>]*)?>\s*Generated\s+\d+\s+puzzles?\s+from\s+\d+\s+games?\.?(?:\s|<br\s*/?>)*</span>)"
        r"\s*"
    )
)
QUESTION_BOARD_STATUS_LINE_PATTERN = re.compile(
    r"(?im)^\s*Generated\s+\d+\s+puzzles?\s+from\s+\d+\s+games?\.?\s*$\n?"
)
QUESTION_BOARD_STATUS_FRAGMENT_PATTERN = re.compile(
    r"(?is)Generated\s+\d+\s+puzzles?\s+from\s+\d+\s+games?\.?(?:\s|<br\s*/?>)*"
)
EMPTY_CONTROL_PARAGRAPH_PATTERN = re.compile(r"<p>(?:\s|<br\s*/?>)*</p>", re.IGNORECASE)


def _build_metric_chip_html(
    value_text: str,
    icon_data_uri: str,
    *,
    description: str = "",
    is_timer: bool = False,
    timer_warning: bool = False,
) -> str:
    timer_class = ""
    if is_timer:
        timer_class = " gm-live-metric--timer"
    if timer_warning:
        timer_class += " gm-live-metric--timer-warning"
    normalized_description = str(description or "").strip()
    escaped_description = escape(normalized_description, quote=True)
    tooltip_html = ""
    if normalized_description:
        tooltip_html = (
            '<span class="gm-live-metric-tooltip" role="tooltip">'
            f"{escape(normalized_description)}"
            "</span>"
        )

    icon_html = ""
    if icon_data_uri:
        icon_html = (
            f'<img class="gm-live-metric-icon" src="{escape(icon_data_uri, quote=True)}" alt="" aria-hidden="true" />'
        )

    return (
        f'<button class="gm-live-metric{timer_class}" type="button"'
        f' aria-label="{escaped_description or escape(value_text, quote=True)}"'
        f' title="{escaped_description or escape(value_text, quote=True)}">'
        f"{icon_html}"
        f'<span class="gm-live-metric-value">{escape(value_text)}</span>'
        f"{tooltip_html}"
        "</button>"
    )


def _build_metrics_bar_html(
    *,
    day_streak_text: str,
    question_streak_text: str,
    rank_text: str,
    timer_text: str,
    timer_warning: bool,
    calendar_icon_data_uri: str,
    fire_icon_data_uri: str,
    podium_icon_data_uri: str,
    timer_icon_data_uri: str,
) -> str:
    return (
        '<section class="gm-quiz-status-block">'
        '<div class="gm-live-metrics-bar">'
        f"{_build_metric_chip_html(day_streak_text, calendar_icon_data_uri, description=DAY_STREAK_DESCRIPTION)}"
        f"{_build_metric_chip_html(question_streak_text, fire_icon_data_uri, description=QUESTION_STREAK_DESCRIPTION)}"
        f"{_build_metric_chip_html(rank_text, podium_icon_data_uri, description=RANK_DESCRIPTION)}"
        f"{_build_metric_chip_html(timer_text, timer_icon_data_uri, description=TIMER_DESCRIPTION, is_timer=True, timer_warning=timer_warning)}"
        "</div>"
        "</section>"
    )


def _build_question_card_html(statement: str) -> str:
    question_html = _move_question_board_controls_below_content(_text_to_html(statement))
    return (
        '<section class="gm-quiz-question-block gm-live-card gm-live-question-card">'
        '<div class="gm-live-card-title">Questão</div>'
        f'<div class="gm-live-question-text">{question_html}</div>'
        "</section>"
    )


def _move_question_board_controls_below_content(question_html: str) -> str:
    cleaned_html = _strip_question_board_status(question_html)
    cleaned_html, source_square = _strip_question_board_move_instruction(cleaned_html)
    cleaned_html = EMPTY_CONTROL_PARAGRAPH_PATTERN.sub("", cleaned_html)
    if "<button" not in cleaned_html.casefold():
        return _prepend_question_board_source_square_highlight(cleaned_html, source_square)

    parser = _QuestionBoardControlParser()
    parser.feed(cleaned_html)
    return _prepend_question_board_source_square_highlight(parser.render(), source_square)


def _strip_question_board_status(question_html: str) -> str:
    without_block_status = QUESTION_BOARD_STATUS_BLOCK_PATTERN.sub("", question_html)
    without_line_status = QUESTION_BOARD_STATUS_LINE_PATTERN.sub("", without_block_status)
    return QUESTION_BOARD_STATUS_FRAGMENT_PATTERN.sub("", without_line_status)


def _strip_question_board_move_instruction(question_html: str) -> tuple[str, str | None]:
    match = QUESTION_BOARD_MOVE_INSTRUCTION_PATTERN.search(question_html)
    if match is None or not _looks_like_question_board_html(question_html):
        return question_html, None

    source_square = match.group("square").casefold()
    return QUESTION_BOARD_MOVE_INSTRUCTION_PATTERN.sub("", question_html), source_square


def _looks_like_question_board_html(question_html: str) -> bool:
    normalized_html = question_html.casefold()
    return any(
        marker in normalized_html
        for marker in (
            "<button",
            "<table",
            "board",
            "chess",
            "square-",
            "data-square",
        )
    )


def _prepend_question_board_source_square_highlight(question_html: str, source_square: str | None) -> str:
    if source_square is None:
        return question_html
    return f"{_build_question_board_source_square_style(source_square)}{question_html}"


def _build_question_board_source_square_style(source_square: str) -> str:
    square = source_square.casefold()
    square_upper = square.upper()
    selectors = (
        f".gm-live-question-text [class~=\"square-{square}\"]",
        f".gm-live-question-text [class~=\"square-{square_upper}\"]",
        f".gm-live-question-text [class~=\"{square}\"]",
        f".gm-live-question-text [class~=\"{square_upper}\"]",
        f".gm-live-question-text #{square}",
        f".gm-live-question-text #{square_upper}",
        f".gm-live-question-text [data-square=\"{square}\"]",
        f".gm-live-question-text [data-square=\"{square_upper}\"]",
        f".gm-live-question-text [data-coord=\"{square}\"]",
        f".gm-live-question-text [data-coord=\"{square_upper}\"]",
        f".gm-live-question-text [data-square-name=\"{square}\"]",
        f".gm-live-question-text [data-square-name=\"{square_upper}\"]",
        f".gm-live-question-text [aria-label~=\"{square}\"]",
        f".gm-live-question-text [aria-label~=\"{square_upper}\"]",
        f".gm-live-question-text [title~=\"{square}\"]",
        f".gm-live-question-text [title~=\"{square_upper}\"]",
    )
    return (
        '<style class="gm-question-board-source-square-style">'
        f"{', '.join(selectors)} "
        "{"
        "background-color: #fde68a !important;"
        "box-shadow: inset 0 0 0 9999px rgba(250, 204, 21, 0.24), inset 0 0 0 3px #f59e0b !important;"
        "outline: 2px solid #f59e0b !important;"
        "outline-offset: -2px !important;"
        "}"
        "</style>"
    )


def _build_info_card_html(message_html: str) -> str:
    return (
        '<section class="gm-live-card gm-live-info-card">'
        f"<div>{message_html}</div>"
        "</section>"
    )


def _build_pending_alternative_card_html(
    *,
    alternative: DisplayAlternative,
    is_selected: bool,
) -> str:
    card_class = "gm-live-card gm-live-pending-choice-card"
    if is_selected:
        card_class += " gm-live-pending-choice-card--selected"

    return (
        f'<section class="{card_class}">'
        f'<div class="gm-live-answer-text">{_text_to_html(alternative.alternative_text)}</div>'
        "</section>"
    )


def _build_answer_review_card_html(
    *,
    alternative: DisplayAlternative,
    selected_option_id: str | None,
) -> str:
    status_class = "gm-live-answer-card"
    badge_text = "Alternativa"

    if alternative.is_correct:
        status_class += " gm-live-answer-card--correct"
        badge_text = "Gabarito"
    else:
        status_class += " gm-live-answer-card--wrong"

    if alternative.option_id == selected_option_id:
        badge_text = "Sua resposta"

    explanation_html = ""
    if alternative.explanation:
        explanation_html = (
            '<div class="gm-live-answer-explanation">'
            f"{_text_to_html(alternative.explanation)}"
            "</div>"
        )

    return (
        f'<section class="gm-live-card {status_class}">'
        f'<div class="gm-live-answer-badge">{escape(badge_text)}</div>'
        f'<div class="gm-live-answer-text">{_text_to_html(alternative.alternative_text)}</div>'
        f"{explanation_html}"
        "</section>"
    )


def _build_answer_status_chip_html(answer_is_correct: bool) -> str:
    status_class = "gm-live-status-chip--correct" if answer_is_correct else "gm-live-status-chip--wrong"
    status_text = "Você acertou" if answer_is_correct else "Você errou"
    return (
        f'<div class="gm-live-status-chip {status_class}">'
        f"{escape(status_text)}"
        "</div>"
    )


def _format_pending_widget_label(markdown_text: str) -> str:
    unwrapped_text = FENCED_CODE_BLOCK_PATTERN.sub(
        lambda match: match.group(1).strip(),
        markdown_text,
    )
    normalized_text = unwrapped_text.strip()
    return normalized_text or markdown_to_plain_text(markdown_text)


class _QuestionBoardControlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._content_parts: list[str] = []
        self._control_parts: list[str] = []
        self._captured_button_parts: list[str] | None = None
        self._captured_button_text: list[str] = []

    def render(self) -> str:
        if self._captured_button_parts is not None:
            self._content_parts.extend(self._captured_button_parts)
            self._captured_button_parts = None
            self._captured_button_text = []

        content_html = "".join(self._content_parts)
        if not self._control_parts:
            return content_html

        content_html = EMPTY_CONTROL_PARAGRAPH_PATTERN.sub("", content_html)
        controls_html = "".join(self._control_parts)
        return (
            f"{content_html}"
            '<div class="gm-question-board-controls">'
            f"{controls_html}"
            "</div>"
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start_tag = self.get_starttag_text() or _format_html_start_tag(tag, attrs)
        if self._captured_button_parts is not None:
            self._captured_button_parts.append(start_tag)
            return
        if tag.casefold() == "button":
            self._captured_button_parts = [start_tag]
            self._captured_button_text = []
            return
        self._content_parts.append(start_tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start_tag = self.get_starttag_text() or _format_html_start_tag(tag, attrs, self_closing=True)
        self._append_html(start_tag)

    def handle_endtag(self, tag: str) -> None:
        end_tag = f"</{tag}>"
        if self._captured_button_parts is None:
            self._content_parts.append(end_tag)
            return

        self._captured_button_parts.append(end_tag)
        if tag.casefold() != "button":
            return

        button_html = "".join(self._captured_button_parts)
        button_label = " ".join("".join(self._captured_button_text).split()).casefold()
        if button_label in QUESTION_BOARD_CONTROL_LABELS:
            self._control_parts.append(button_html)
        else:
            self._content_parts.append(button_html)
        self._captured_button_parts = None
        self._captured_button_text = []

    def handle_data(self, data: str) -> None:
        html = escape(data, quote=False)
        if self._captured_button_parts is not None:
            self._captured_button_parts.append(html)
            self._captured_button_text.append(data)
            return
        self._content_parts.append(html)

    def handle_entityref(self, name: str) -> None:
        self._append_html(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._append_html(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._append_html(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._append_html(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self._append_html(f"<?{data}>")

    def _append_html(self, html: str) -> None:
        if self._captured_button_parts is not None:
            self._captured_button_parts.append(html)
            return
        self._content_parts.append(html)


def _format_html_start_tag(
    tag: str,
    attrs: list[tuple[str, str | None]],
    *,
    self_closing: bool = False,
) -> str:
    attr_html = "".join(
        f' {name}="{escape(value, quote=True)}"' if value is not None else f" {name}"
        for name, value in attrs
    )
    suffix = " /" if self_closing else ""
    return f"<{tag}{attr_html}{suffix}>"


def _text_to_html(text: str | None) -> str:
    return markdown_to_html(text)
