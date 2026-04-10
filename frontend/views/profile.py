"""
frontend/views/profile.py
Owner: Jonas Chen

Responsibilities:
- Renders the user profile page
- Displays taste preferences and saved restaurants
- Connects profile preferences to frontend state
- Supports jumping from saved restaurants back to Discover
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results
from frontend.components.empty_state import render_empty_state
from frontend.components.profile_form import render_profile_form
from frontend.components.restaurant_card import render_restaurant_card


def render_profile(restaurants: list[dict]) -> None:
    normalized = normalize_results(restaurants or [])

    index = {
        item.get("business_id"): item
        for item in normalized
        if item.get("business_id")
    }

    saved_ids = st.session_state.get("saved_ids", []) or []
    saved_restaurants = [index[item_id] for item_id in saved_ids if item_id in index]

    left, right = st.columns([1.15, 1.85], gap="large")

    with left:
        st.markdown(
            "<div class='nb-panel-title'>Taste profile</div>",
            unsafe_allow_html=True,
        )
        render_profile_form(restaurants)

    with right:
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
        else:
            for idx, item in enumerate(saved_restaurants):
                render_restaurant_card(item, key_prefix=f"profile_saved_{idx}")