"""
frontend/views/home.py
Owner: Jonas Chen

Responsibilities:
- Renders the NearBite homepage
- Displays the hero section, search bar, and summary statistics
- Shows top restaurant picks for the current session
- Connects homepage interactions to the Discover page
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results, sort_results
from frontend.components.hero import render_home_hero
from frontend.components.restaurant_card import render_restaurant_card


def render_home(restaurants: list[dict]) -> None:
    render_home_hero()

    normalized = normalize_results(restaurants)
    focus_id = st.session_state.get("focus_business_id")
    ordered = sort_results(restaurants, focus_id)

    search_cols = st.columns([5.2, 1.2], gap="small")
    with search_cols[0]:
        st.session_state.search_query = st.text_input(
            "Search",
            value=st.session_state.get(
                "search_query",
                "cheap spicy noodles near washington square",
            ),
            label_visibility="collapsed",
            placeholder="cheap spicy noodles near washington square",
        )
    with search_cols[1]:
        if st.button("Search", use_container_width=True):
            st.session_state.page = "Discover"
            st.rerun()

    stat_cols = st.columns(3, gap="large")
    with stat_cols[0]:
        st.markdown(
            f"""
            <div class="nb-panel">
              <div class="nb-panel-title">Restaurants in dataset</div>
              <div class="nb-wrap-value">{len(normalized)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with stat_cols[1]:
        st.markdown(
            f"""
            <div class="nb-panel">
              <div class="nb-panel-title">Saved places</div>
              <div class="nb-wrap-value">{len(st.session_state.get("saved_ids", []))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with stat_cols[2]:
        avg_rating = (
            sum(item.get("rating", 0.0) for item in normalized) / len(normalized)
            if normalized
            else 0.0
        )
        st.markdown(
            f"""
            <div class="nb-panel">
              <div class="nb-panel-title">Average rating</div>
              <div class="nb-wrap-value">⭐ {avg_rating:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div class='nb-section-title'>Top picks for you</div>",
        unsafe_allow_html=True,
    )

    top_picks = ordered[:6]
    cols = st.columns(2, gap="large")
    for idx, item in enumerate(top_picks):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"home_{idx}")