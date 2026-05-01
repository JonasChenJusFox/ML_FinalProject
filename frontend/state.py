"""Default session keys for navigation, search, filters, and profile-related UI."""

from __future__ import annotations

import streamlit as st


DEFAULT_PROFILE = {
    "favorite_cuisines": ["Thai", "Japanese", "Chinese"],
    "dietary": [],
    "price_level": 2,
    "travel_radius_min": 25,
    "vibes": ["cozy", "casual", "quiet"],
}

DEFAULT_FILTERS = {
    "cuisines": [],
    "price_levels": [],
    "min_rating": 0.0,
    "borough": "All",
    "travel_radius_min": 30,
    "sort_by": "Relevance",
}


def init_state(preview_restaurants: list[dict]) -> None:
    if "use_my_location" not in st.session_state:
        st.session_state.use_my_location = False

    if "user_lat" not in st.session_state:
        st.session_state.user_lat = None

    if "user_lon" not in st.session_state:
        st.session_state.user_lon = None

    if "user_origin_label" not in st.session_state:
        st.session_state.user_origin_label = "NYU"

    if "page" not in st.session_state:
        st.session_state.page = "Home"

    if "search_query" not in st.session_state:
        st.session_state.search_query = ""

    if "profile" not in st.session_state:
        st.session_state.profile = DEFAULT_PROFILE.copy()

    if "filters" not in st.session_state:
        st.session_state.filters = DEFAULT_FILTERS.copy()

    if "saved_ids" not in st.session_state:
        st.session_state.saved_ids = []

    if "liked_ids" not in st.session_state:
        st.session_state.liked_ids = []

    if "interaction_map" not in st.session_state:
        st.session_state.interaction_map = {}

    if "viewed_ids" not in st.session_state:
        st.session_state.viewed_ids = []

    if "preview_restaurants" not in st.session_state:
        st.session_state.preview_restaurants = preview_restaurants or []
