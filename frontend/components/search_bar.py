"""
frontend/components/search_bar.py
Owner: Jonas Chen

Responsibilities:
- Renders the main search bar UI for restaurant discovery
- Collects natural-language search queries from the user
- Connects search input to Streamlit session state
- Supports query reuse across Home and Discover pages
"""

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