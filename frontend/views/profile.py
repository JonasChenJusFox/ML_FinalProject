"""
frontend/views/profile.py
Owner: Jonas Chen

Responsibilities:
- Renders the combined profile page
- Displays database-backed wrapped summary at the top
- Displays saved restaurants below the summary
- Provides a button to enter the recommendation flow
- Connects profile actions to frontend state and login flow
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results
from frontend.auth import open_login_modal
from frontend.components.empty_state import render_empty_state
from frontend.components.restaurant_card import render_restaurant_card
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
        st.info("Please log in to view your profile and saved restaurants.")
        if st.button("Log in", key="profile_login_button"):
            open_login_modal()
            st.rerun()
        return

    current_user = st.session_state.get("current_user", {})
    username = current_user.get("username", "")

    if not username:
        st.info("Please log in to view your profile and saved restaurants.")
        if st.button("Log in", key="profile_login_button_fallback"):
            open_login_modal()
            st.rerun()
        return

    normalized = normalize_results(restaurants or [])

    restaurant_index = {
        item.get("business_id"): item
        for item in normalized
        if item.get("business_id")
    }

    saved_ids = st.session_state.get("saved_ids", []) or []
    saved_restaurants = [restaurant_index[item_id] for item_id in saved_ids if item_id in restaurant_index]

    wrapped = build_wrapped_stats(username, normalized)

    top_row = st.columns([2.2, 1], gap="large")

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
            "<div class='nb-section-title'>Recommendation</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "Need recommendation",
            key="profile_need_recommendation",
            use_container_width=True,
        ):
            st.session_state.page = "Recommendation"
            st.rerun()

    st.markdown(
        "<div class='nb-section-title'>Saved restaurants</div>",
        unsafe_allow_html=True,
    )
    st.caption("Use Focus map to jump to Discover and move that restaurant to the top.")

    if not saved_restaurants:
        render_empty_state(
            "Nothing saved yet",
            "Save a few restaurants from Discover and they will appear here.",
        )
        return

    for idx, item in enumerate(saved_restaurants):
        render_restaurant_card(item, key_prefix=f"profile_saved_{idx}")