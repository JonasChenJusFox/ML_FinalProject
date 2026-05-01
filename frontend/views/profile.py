"""Profile: wrapped summary, saved restaurants, onboarding form, and login gates."""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results
from frontend.auth import open_login_modal, open_signup_modal
from frontend.components.empty_state import render_empty_state
from frontend.components.restaurant_card import render_restaurant_card
from frontend.user_profile_state import get_questionnaire_answers
from integration.interaction_repo import get_user_interaction_records
from integration.wrapped_repo import build_wrapped_stats


def render_profile(restaurants: list[dict]) -> None:
    """
    Render the merged Profile page with:
    - wrapped summary
    - saved restaurants
    - recommendation entry point
    """
    st.markdown("### Profile")

    if not st.session_state.get("is_logged_in", False):
        st.info("Log in or create an account to complete your questionnaire and keep private saved, liked, and reviewed places.")
        gate_cols = st.columns(2, gap="small")
        if gate_cols[0].button("Log in", key="profile_login_button", use_container_width=True):
            st.session_state.post_login_redirect = "profile"
            open_login_modal()
            st.rerun()
        if gate_cols[1].button("Create account", key="profile_signup_button", use_container_width=True):
            st.session_state.post_login_redirect = "profile"
            open_signup_modal()
            st.rerun()
        return

    current_user = st.session_state.get("current_user", {})
    username = current_user.get("username", "")

    if not username:
        st.info("Please log in to view your profile.")
        if st.button("Log in", key="profile_login_button_fallback"):
            st.session_state.post_login_redirect = "profile"
            open_login_modal()
            st.rerun()
        return

    normalized = normalize_results(restaurants or [])

    restaurant_index = {
        item.get("business_id"): item
        for item in normalized
        if item.get("business_id")
    }

    interaction_records = get_user_interaction_records(username)
    interaction_restaurants = [
        restaurant_index[record["business_id"]]
        for record in interaction_records
        if record.get("business_id") in restaurant_index
    ]

    wrapped = build_wrapped_stats(username, normalized)

    top_row = st.columns([2.1, 1.2], gap="large")

    with top_row[0]:
        st.markdown(
            "<div class='nb-section-title'>Wrapped summary</div>",
            unsafe_allow_html=True,
        )

        summary_cols = st.columns(4, gap="small")

        summary_cols[0].markdown(
            f"""
            <div class="nb-wrap-card">
              <div class="nb-panel-title">Saved places</div>
              <div class="nb-wrap-value">{wrapped.get('saved_count', 0)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        top_cuisine = ", ".join(wrapped.get("top_cuisines", [])[:2]) or "Not enough data yet"
        summary_cols[1].markdown(
            f"""
            <div class="nb-wrap-card">
              <div class="nb-panel-title">Top cuisine</div>
              <div class="nb-wrap-value">{top_cuisine}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        top_borough = ", ".join(wrapped.get("top_boroughs", [])[:2]) or "Not enough data yet"
        summary_cols[2].markdown(
            f"""
            <div class="nb-wrap-card">
              <div class="nb-panel-title">Top borough</div>
              <div class="nb-wrap-value">{top_borough}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        interaction_count = wrapped.get("interaction_count", 0)
        summary_cols[3].markdown(
            f"""
            <div class="nb-wrap-card">
              <div class="nb-panel-title">Interactions</div>
              <div class="nb-wrap-value">{interaction_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_row[1]:
        st.markdown(
            "<div class='nb-section-title'>Profile setup</div>",
            unsafe_allow_html=True,
        )

        onboarding_completed = st.session_state.get("onboarding_completed", False)
        questionnaire_label = "Edit questionnaire" if onboarding_completed else "Complete questionnaire"
        if st.button(questionnaire_label, key="profile_edit_questionnaire", use_container_width=True):
            st.session_state.show_post_signup_questionnaire = True
            st.rerun()

        current_answers = get_questionnaire_answers()
        cuisines_preview = ", ".join(current_answers.get("top_cuisines", [])[:3]) or "Not set yet"
        meals_preview = ", ".join(current_answers.get("typical_meals", [])[:3]) or "Not set yet"
        st.caption(f"Top cuisines: {cuisines_preview}")
        st.caption(f"Typical meals: {meals_preview}")

    st.markdown(
        "<div class='nb-section-title'>Your interactions</div>",
        unsafe_allow_html=True,
    )
    st.caption("Saved, liked, and reviewed restaurants appear here with your private notes.")

    if not interaction_restaurants:
        render_empty_state(
            "No interactions yet",
            "Save, like, or review a few restaurants from Discover and they will appear here.",
        )
        return

    for idx, item in enumerate(interaction_restaurants):
        render_restaurant_card(item, key_prefix=f"profile_saved_{idx}")
