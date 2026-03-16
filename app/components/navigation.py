from __future__ import annotations

from urllib.parse import urlencode

import streamlit as st


def get_query_param(name: str) -> str | None:
    """Return a single query-parameter value when present."""

    value = st.query_params.get(name)
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    text = str(value).strip()
    return text or None


def consume_query_param(name: str) -> str | None:
    """Return and remove one query parameter."""

    value = get_query_param(name)
    if value is None:
        return None
    clear_query_param(name)
    return value


def clear_query_param(name: str) -> None:
    """Remove one query parameter when present."""

    if name in st.query_params:
        del st.query_params[name]


def build_query_link(**updates: str | None) -> str:
    """Build a lightweight in-app link preserving only stable UI state."""

    params: dict[str, str] = {}
    theme = get_query_param("theme")
    if theme in {"dark", "light"}:
        params["theme"] = theme

    for key, value in updates.items():
        if value is None:
            params.pop(key, None)
            continue
        text = str(value).strip()
        if text:
            params[key] = text
        else:
            params.pop(key, None)

    return f"?{urlencode(params)}" if params else ""
