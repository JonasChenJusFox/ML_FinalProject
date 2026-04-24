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

from collections.abc import Callable

import streamlit as st


HOME_PLACEHOLDER = "highly rated spicy noodles near washington square, late-night ramen in east village"
DISCOVER_PLACEHOLDER = "highly rated halal near me, quiet cafe in soho, sushi near washington square"


def render_search_bar(
    key: str = "search_query",
    placeholder: str = DISCOVER_PLACEHOLDER,
    on_change: Callable[[], None] | None = None,
) -> str:
    query = st.text_input(
        "Search",
        key=key,
        placeholder=placeholder,
        label_visibility="collapsed",
        on_change=on_change,
    )
    st.caption("Press Enter to Search or click the Search button.")
    return query.strip()
