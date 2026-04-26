"""
frontend/components/profile_form.py
Owner: Jonas Chen

Responsibilities:
- Renders the profile preference form
- Collects favorite cuisines, dietary preferences, price comfort, and vibe preferences
- Stores frontend profile choices in session state
- Supports the demo version of personalization without database persistence
"""

from __future__ import annotations

import streamlit as st


VIBE_OPTIONS = [
    "cozy",
    "quiet",
    "casual",
    "date night",
    "late night",
    "group dinner",
    "study-friendly",
]

DIETARY_OPTIONS = [
    "Vegetarian",
    "Vegan",
    "Halal",
    "Gluten-free",
]


def _valid_defaults(defaults: list[str], options: list[str]) -> list[str]:
    option_set = set(options)
    return [item for item in defaults if item in option_set]


def render_profile_form(restaurants: list[dict]) -> None:
    filter_options = st.session_state.get("filter_options", {})

    cuisine_options = filter_options.get("categories", [])
    price_options = filter_options.get("prices", [])
    if not price_options:
        price_options = ["$", "$$", "$$$", "$$$$"]

    profile = st.session_state.get(
        "profile",
        {
            "favorite_cuisines": [],
            "dietary_preferences": [],
            "price_comfort": "$$",
            "travel_radius": 25,
            "vibe_preferences": [],
        },
    )

    favorite_cuisine_defaults = _valid_defaults(
        profile.get("favorite_cuisines", []),
        cuisine_options,
    )

    dietary_defaults = _valid_defaults(
        profile.get("dietary_preferences", []),
        DIETARY_OPTIONS,
    )

    vibe_defaults = _valid_defaults(
        profile.get("vibe_preferences", []),
        VIBE_OPTIONS,
    )

    price_default = profile.get("price_comfort", "$$")
    if price_default not in price_options:
        price_default = price_options[0]

    travel_radius_default = profile.get("travel_radius", 25)
    if not isinstance(travel_radius_default, int):
        travel_radius_default = 25

    with st.form("profile_form"):
        favorite_cuisines = st.multiselect(
            "Favorite cuisines",
            options=cuisine_options,
            default=favorite_cuisine_defaults,
        )

        dietary_preferences = st.multiselect(
            "Dietary preferences",
            options=DIETARY_OPTIONS,
            default=dietary_defaults,
        )

        price_comfort = st.selectbox(
            "Price comfort",
            options=price_options,
            index=price_options.index(price_default),
        )

        travel_radius = st.slider(
            "Preferred travel radius from NYU (minutes)",
            min_value=5,
            max_value=120,
            value=travel_radius_default,
            step=5,
        )

        vibe_preferences = st.multiselect(
            "Vibe preferences",
            options=VIBE_OPTIONS,
            default=vibe_defaults,
        )

        submitted = st.form_submit_button("Save profile", use_container_width=True)

    if submitted:
        st.session_state.profile = {
            "favorite_cuisines": favorite_cuisines,
            "dietary_preferences": dietary_preferences,
            "price_comfort": price_comfort,
            "travel_radius": travel_radius,
            "vibe_preferences": vibe_preferences,
        }
        st.toast("Profile saved.")