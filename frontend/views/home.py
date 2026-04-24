"""
frontend/views/home.py
Owner: Jonas Chen

Responsibilities:
- Renders the simplified NearBite homepage
- Displays the main search bar and direct route into Discover
- Hosts the questionnaire flow for logged-in users
- Shows recommendation or nearby restaurant cards below the search area
"""

from __future__ import annotations

import math
import random

import streamlit as st

from frontend.adapters import normalize_results
from frontend.auth import open_login_modal, open_questionnaire_modal
from frontend.components.restaurant_card import render_restaurant_card
from frontend.components.search_bar import HOME_PLACEHOLDER, render_search_bar
from frontend.user_profile_state import init_user_profile_state
from integration.api import search_restaurants


def _commit_home_search(query: str) -> None:
    committed_query = query.strip()
    st.session_state.search_query = committed_query
    st.session_state.discover_query = committed_query
    st.session_state.discover_active_query = committed_query
    st.session_state.discover_page = 1
    st.session_state.page = "Discover"


def _search_from_home(query: str) -> None:
    _commit_home_search(query)
    st.rerun()


def _score_home_popularity(item: dict, seed: int) -> float:
    rating = float(item.get("rating", 0.0) or 0.0)
    review_count = float(item.get("review_count", 0.0) or 0.0)
    business_id = str(item.get("business_id", ""))
    jitter = random.Random(f"{seed}:{business_id}").uniform(0.0, 0.18)
    popularity = math.log1p(max(0.0, review_count))
    return (rating * 1.35) + (popularity * 0.55) + jitter


def _frontend_home_fallback(restaurants: list[dict]) -> list[dict]:
    normalized = normalize_results(restaurants or [])
    seed = int(st.session_state.get("home_random_seed", 0) or 0)
    ranked = sorted(
        normalized,
        key=lambda item: _score_home_popularity(item, seed),
        reverse=True,
    )
    return ranked[:10]


def render_home(restaurants: list[dict]) -> None:
    init_user_profile_state()
    if "home_search_query" not in st.session_state:
        st.session_state.home_search_query = st.session_state.get("search_query", "")
    if "home_random_seed" not in st.session_state:
        st.session_state.home_random_seed = random.randint(1, 10_000_000)

    st.markdown("## Looking for great food nearby? Just use NearBite.")

    search_cols = st.columns([6.0, 1.0], gap="small")
    with search_cols[0]:
        render_search_bar(
            key="home_search_query",
            placeholder=HOME_PLACEHOLDER,
            on_change=lambda: _commit_home_search(st.session_state.get("home_search_query", "")),
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
    else:
        onboarding_completed = st.session_state.get("onboarding_completed", False)
        button_label = "Edit answers" if onboarding_completed else "Questionnaire"
        helper_text = (
            "Update your answers any time to refresh your recommendation profile."
            if onboarding_completed
            else "Help us to make better recommendations for you."
        )

        if st.button(
            button_label,
            key="home_questionnaire_button",
            use_container_width=False,
        ):
            open_questionnaire_modal()
            st.rerun()
        st.caption(helper_text)

    if user_id == "anonymous":
        ranked = _frontend_home_fallback(restaurants)
        section_title = "Popular restaurants"
    else:
        ranked = normalize_results(
            search_restaurants(
                query="",
                filters=None,
                user_id=user_id,
                top_k=10,
                user_vector_only=True,
            )
        )
        if not ranked:
            ranked = _frontend_home_fallback(restaurants)
        section_title = "Recommended restaurants"

    showing_nearby = user_id == "anonymous"
    st.markdown(
        f"<div class='nb-section-title'>{section_title}</div>",
        unsafe_allow_html=True,
    )

    if not ranked:
        st.info("No recommendations available yet.")
        return

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(ranked[:10]):
    for idx, item in enumerate(ordered[:10]):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"home_{idx}")
