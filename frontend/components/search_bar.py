"""Natural-language search input wired to ``st.session_state`` for Home and Discover."""

from __future__ import annotations

import streamlit as st


HOME_PLACEHOLDER = "cheap spicy noodles near washington square"
DISCOVER_PLACEHOLDER = "cozy date night spot in manhattan"


def render_search_bar(key: str = "search_query", placeholder: str = DISCOVER_PLACEHOLDER) -> str:
    query = st.text_input(
        "Search",
        key=key,
        placeholder=placeholder,
        label_visibility="collapsed",
    )
    return query.strip()