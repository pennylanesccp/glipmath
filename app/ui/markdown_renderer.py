from __future__ import annotations

import re
from functools import lru_cache

import markdown

MARKDOWN_EXTENSIONS = (
    "fenced_code",
    "tables",
    "nl2br",
    "sane_lists",
)

_INLINE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
_FENCED_CODE_PATTERN = re.compile(r"```(?:[\w+-]+)?\n(.*?)```", re.S)


def markdown_to_html(text: str | None) -> str:
    """Render safe-ish Markdown for question statements and explanations."""

    normalized_text = str(text or "").strip()
    if not normalized_text:
        return ""
    return _render_markdown_html(normalized_text)


def markdown_to_plain_text(text: str | None) -> str:
    """Collapse common Markdown markers into a readable plain-text label."""

    normalized_text = str(text or "").strip()
    if not normalized_text:
        return ""
    plain_text = _FENCED_CODE_PATTERN.sub(lambda match: match.group(1).strip(), normalized_text)
    plain_text = _INLINE_LINK_PATTERN.sub(lambda match: match.group(1), plain_text)
    plain_text = _INLINE_CODE_PATTERN.sub(lambda match: match.group(1), plain_text)
    plain_text = plain_text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    return plain_text.strip()


@lru_cache(maxsize=256)
def _render_markdown_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=list(MARKDOWN_EXTENSIONS),
        output_format="html5",
    )
