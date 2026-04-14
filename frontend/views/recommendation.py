"""
frontend/views/recommendation.py
Owner: Jonas Chen

Responsibilities:
- Renders the recommendation page for logged-in users
- Shows onboarding questionnaire for first-time recommendation flow
- Allows editing existing questionnaire answers
- Displays top recommended restaurants using the shared restaurant card UI
- Normalizes restaurant data before scoring and rendering
- Uses database-backed wrapped stats for personalization
- Connects questionnaire answers and wrapped signals to the recommendation algorithm
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results
from frontend.auth import open_login_modal
from frontend.components.onboarding_form import render_onboarding_form
from frontend.components.restaurant_card import render_restaurant_card
from frontend.user_profile_state import get_questionnaire_answers, init_user_profile_state
from integration.wrapped_repo import build_wrapped_stats
from recommendation.algorithm import recommend_top_restaurants


def _init_recommendation_state() -> None:
    if "editing_questionnaire" not in st.session_state:
        st.session_state.editing_questionnaire = False


def render_recommendation(restaurants: list[dict]) -> None:
    init_user_profile_state()
    _init_recommendation_state()

    st.markdown("### Recommendation")

    if not st.session_state.get("is_logged_in", False):
        st.info("Please log in to receive personalized recommendations.")
        if st.button("Log in", key="recommendation_login_button"):
            open_login_modal()
            st.rerun()
        return

    current_user = st.session_state.get("current_user", {})
    username = current_user.get("username", "")

    if not username:
        st.info("Please log in to receive personalized recommendations.")
        if st.button("Log in", key="recommendation_login_button_fallback"):
            open_login_modal()
            st.rerun()
        return

    normalized_restaurants = normalize_results(restaurants or [])

    onboarding_completed = st.session_state.get("onboarding_completed", False)
    editing_questionnaire = st.session_state.get("editing_questionnaire", False)

    top_row = st.columns([1.2, 1], gap="small")

    with top_row[0]:
        st.markdown(
            "<div class='nb-section-title'>Personalized recommendations</div>",
            unsafe_allow_html=True,
        )

    with top_row[1]:
        if onboarding_completed and not editing_questionnaire:
            if st.button(
                "Edit answers",
                key="recommendation_edit_answers",
                use_container_width=True,
            ):
                st.session_state.editing_questionnaire = True
                st.rerun()

    if not onboarding_completed or editing_questionnaire:
        st.caption(
            "Complete or update the questionnaire to unlock your personalized restaurant recommendations."
        )
        render_onboarding_form()
        return

    answers = get_questionnaire_answers()
    wrapped_stats = build_wrapped_stats(username, normalized_restaurants)

    ranked = recommend_top_restaurants(
        restaurants=normalized_restaurants,
        questionnaire_answers=answers,
        wrapped_stats=wrapped_stats,
        top_k=10,
    )

    if not ranked:
        st.warning("No recommendations available yet.")
        return

    st.markdown(
        "<div class='nb-section-title'>Top 10 restaurants for you</div>",
        unsafe_allow_html=True,
    )

    for idx, item in enumerate(ranked):
        render_restaurant_card(item, key_prefix=f"recommendation_{idx}")