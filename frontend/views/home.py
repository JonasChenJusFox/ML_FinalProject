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

import streamlit as st

from frontend.adapters import get_current_origin_kwargs, normalize_results
from frontend.auth import open_login_modal, open_questionnaire_modal
from frontend.components.restaurant_card import render_restaurant_card
from frontend.components.search_bar import HOME_PLACEHOLDER, render_search_bar
from frontend.user_profile_state import init_user_profile_state
from integration.api import get_recommendations_for_user, search_restaurants
from integration.wrapped_repo import build_wrapped_stats


def _search_from_home(query: str) -> None:
    committed_query = query.strip()
    st.session_state.search_query = committed_query
    st.session_state.discover_query = committed_query
    st.session_state.discover_active_query = committed_query
    st.session_state.discover_page = 1
    st.session_state.page = "Discover"
    st.rerun()


def _should_use_nearby_fallback(
    user_id: str,
    restaurants: list[dict],
) -> bool:
    if user_id == "anonymous":
        return True

    if st.session_state.get("onboarding_completed", False):
        return False

    wrapped_stats = build_wrapped_stats(user_id, restaurants)
    return not (
        wrapped_stats.get("saved_count", 0)
        or wrapped_stats.get("reviewed_count", 0)
    )


def _get_home_recommendations(
    user_id: str,
    origin_kwargs: dict,
    restaurants: list[dict],
) -> tuple[list[dict], bool]:
    use_nearby_fallback = _should_use_nearby_fallback(user_id, restaurants)

    if use_nearby_fallback:
        nearby = search_restaurants(
            query="",
            filters=None,
            user_id="anonymous",
            top_k=10,
            user_vector_only=False,
            **origin_kwargs,
        )
        return nearby, True

    ranked = get_recommendations_for_user(
        user_id=user_id,
        top_k=10,
        candidate_top_k=60,
        filters=None,
        **origin_kwargs,
    )
    if ranked:
        return ranked, False

    return (
        search_restaurants(
            query="",
            filters=None,
            user_id=user_id,
            top_k=10,
            user_vector_only=True,
            **origin_kwargs,
        ),
        False,
    )


def render_home(restaurants: list[dict]) -> None:
    init_user_profile_state()
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
    origin_kwargs = get_current_origin_kwargs()

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

    ranked, showing_nearby = _get_home_recommendations(
        user_id,
        origin_kwargs,
        restaurants,
    )
    ranked = normalize_results(ranked or restaurants or [])

    st.markdown(
        (
            "<div class='nb-section-title'>Nearby restaurants</div>"
            if showing_nearby
            else "<div class='nb-section-title'>Recommended restaurants</div>"
        ),
        unsafe_allow_html=True,
    )

    if not ranked:
        st.info("No recommendations available yet.")
        return

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(ranked[:10]):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"home_{idx}")
