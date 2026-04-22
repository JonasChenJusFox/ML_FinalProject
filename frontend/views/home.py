"""
frontend/views/home.py
Owner: Jonas Chen

Responsibilities:
- Renders the simplified NearBite homepage
- Displays the main search bar and direct route into Discover
- Shows recommendation or nearby restaurant cards below the search area
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results, sort_results
from frontend.auth import open_login_modal
from frontend.components.restaurant_card import render_restaurant_card
from frontend.components.search_bar import HOME_PLACEHOLDER, render_search_bar
from integration.api import search_restaurants


def _search_from_home(query: str) -> None:
    committed_query = query.strip()
    st.session_state.search_query = committed_query
    st.session_state.page = "Discover"
    st.rerun()


def render_home(restaurants: list[dict]) -> None:
    if "home_search_query" not in st.session_state:
        st.session_state.home_search_query = st.session_state.get("search_query", "")

    st.markdown("## Looking for great food nearby? Just use NearBite.")

    search_cols = st.columns([6.0, 1.0], gap="small")
    with search_cols[0]:
        render_search_bar(
            key="home_search_query",
            placeholder=HOME_PLACEHOLDER,
        )
    with search_cols[1]:
        if st.button("Search", key="home_search_button", use_container_width=True):
            _search_from_home(st.session_state.get("home_search_query", ""))

    current_user = st.session_state.get("current_user", {}) or {}
    user_id = current_user.get("username") or "anonymous"

    if user_id == "anonymous":
        st.caption("Log in if you want questionnaire-based personalized recommendations.")
        if st.button("Log in for personalization", key="home_login_for_personalization"):
            open_login_modal()
            st.rerun()

    recommendation_source = restaurants
    if user_id != "anonymous":
        recommendation_source = search_restaurants(
            query="",
            filters=None,
            user_id=user_id,
            top_k=10,
            user_vector_only=True,
        )

    normalized = normalize_results(recommendation_source)
    focus_id = st.session_state.get("focus_business_id")
    ordered = sort_results(normalized, focus_id)

    showing_nearby = user_id == "anonymous"
    st.markdown(
        (
            "<div class='nb-section-title'>Nearby restaurants</div>"
            if showing_nearby
            else "<div class='nb-section-title'>Recommended restaurants</div>"
        ),
        unsafe_allow_html=True,
    )

    if not ordered:
        st.info("No recommendations available yet.")
        return

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(ordered[:10]):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"home_{idx}")