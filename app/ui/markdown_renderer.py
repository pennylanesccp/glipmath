from __future__ import annotations

import html
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

_MATH_SUBSCRIPT_PATTERN = re.compile(r"\$?([A-Za-z]+)_\{((?:[^{}]|\{[^}]*\})*)\}\$?")
_TEXT_COMMAND_PATTERN = re.compile(r"\\text\{([^}]+)\}")
_PLACEHOLDER_PREFIX = "___CODE_BLOCK_"
_PLACEHOLDER_SUFFIX = "___"


def _clean_subscript(sub: str) -> str:
    sub = _TEXT_COMMAND_PATTERN.sub(r"\1", sub)
    sub = sub.replace("\\", "")
    return sub.strip()


def _normalize_math_subscripts(text: str) -> str:
    placeholders = {}

    def fence_repl(match: re.Match) -> str:
        pid = f"{_PLACEHOLDER_PREFIX}{len(placeholders)}{_PLACEHOLDER_SUFFIX}"
        placeholders[pid] = match.group(0)
        return pid

    # Protect code blocks
    text = _FENCED_CODE_PATTERN.sub(fence_repl, text)
    text = _INLINE_CODE_PATTERN.sub(fence_repl, text)

    def math_repl(match: re.Match) -> str:
        base_var = html.escape(match.group(1))
        sub_raw = match.group(2)
        cleaned_sub = html.escape(_clean_subscript(sub_raw))
        return f"{base_var}<sub>{cleaned_sub}</sub>"

    # Normalize math
    text = _MATH_SUBSCRIPT_PATTERN.sub(math_repl, text)

    # Restore code blocks
    for pid, original_code in placeholders.items():
        text = text.replace(pid, original_code)

    return text


def markdown_to_html(text: str | None) -> str:
    """Render safe-ish Markdown for question statements and explanations."""

    normalized_text = str(text or "").strip()
    if not normalized_text:
        return ""
    normalized_text = _normalize_math_subscripts(normalized_text)
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
