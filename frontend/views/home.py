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

from frontend.adapters import normalize_results
from frontend.auth import open_login_modal, open_signup_modal
from frontend.components.restaurant_card import render_restaurant_card
from frontend.components.search_bar import HOME_PLACEHOLDER
from integration.api import search_restaurants


def _search_from_home(query: str) -> None:
    committed_query = query.strip()
    st.session_state.search_query = committed_query
    st.session_state.page = "Discover"
    st.rerun()


def render_home(restaurants: list[dict]) -> None:
    if "home_search_query" not in st.session_state:
        st.session_state.home_search_query = st.session_state.get("search_query", "")

    st.markdown("## Find restaurants with one simple search")
    st.caption("Use natural language like `cheap tacos in LES`, then refine in Discover only if you want to.")

    with st.form("home_search_form", clear_on_submit=False):
        search_cols = st.columns([6.0, 1.0], gap="small")
        with search_cols[0]:
            st.text_input(
                "Search",
                key="home_search_query",
                placeholder=HOME_PLACEHOLDER,
                label_visibility="collapsed",
            )
        with search_cols[1]:
            submitted = st.form_submit_button("Search", use_container_width=True)
        if submitted:
            _search_from_home(st.session_state.get("home_search_query", ""))

    current_user = st.session_state.get("current_user", {}) or {}
    user_id = current_user.get("username") or "anonymous"

    if user_id == "anonymous":
        st.info("Browsing anonymously shows a simple default feed. Log in to save places, answer the questionnaire, and personalize results.")
        auth_cols = st.columns(2, gap="small")
        if auth_cols[0].button("Log in", key="home_login_for_personalization", use_container_width=True):
            open_login_modal()
            st.rerun()
        if auth_cols[1].button("Create account", key="home_signup_for_personalization", use_container_width=True):
            open_signup_modal()
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

    ordered = normalize_results(recommendation_source)

    showing_nearby = user_id == "anonymous"
    st.markdown(
        (
            "<div class='nb-section-title nb-section-title-strong'>POPULAR AROUND NYU</div>"
            if showing_nearby
            else "<div class='nb-section-title nb-section-title-strong'>FOR YOU RIGHT NOW</div>"
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        "Anonymous users see a simple browse feed."
        if showing_nearby
        else "These recommendations come directly from the shared search/ranking pipeline using your profile and interactions."
    )

    if not ordered:
        st.info("No recommendations available yet.")
        return

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(ordered[:10]):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"home_{idx}")
