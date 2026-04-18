"""
frontend/views/discover.py
Owner: Jonas Chen

Responsibilities:
- Renders the main restaurant discovery page
- Displays filters, map results, and restaurant cards
- Applies query-based and structured frontend filtering
- Supports focus-map behavior and result reordering
- Controls how many restaurant cards are shown at once
- Logs viewed restaurant cards for wrapped-style personalization
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import clean_text, normalize_results, sort_results
from frontend.components.empty_state import render_empty_state
from frontend.components.location_picker import render_location_picker
from frontend.components.map_view import render_map
from frontend.components.restaurant_card import render_restaurant_card
from integration.api import search_restaurants
from integration.wrapped_repo import log_user_interaction


SHOW_OPTIONS = [12, 24, 36, 48, "All"]


def _matches_query(item: dict, query: str) -> bool:
    q = clean_text(query).lower()
    if not q:
        return True

    haystack = " ".join(
        [
            clean_text(item.get("name", "")),
            clean_text(item.get("borough", "")),
            " ".join(item.get("categories", [])),
            clean_text(item.get("address", "")),
            clean_text(item.get("review_snippet", "")),
        ]
    ).lower()

    return all(token in haystack for token in q.split())


def _passes_filters(
    item: dict,
    query: str,
    selected_categories: list[str],
    selected_borough: str,
    selected_prices: list[str],
    min_rating: float,
    radius_minutes: int,
) -> bool:
    if query and not _matches_query(item, query):
        return False

    if selected_categories:
        restaurant_categories = {c.lower() for c in item.get("categories", [])}
        selected_set = {c.lower() for c in selected_categories}
        if restaurant_categories.isdisjoint(selected_set):
            return False

    if selected_borough != "All" and item.get("borough") != selected_borough:
        return False

    if selected_prices and item.get("price_display") not in selected_prices:
        return False

    if float(item.get("rating", 0.0) or 0.0) < min_rating:
        return False

    if int(item.get("travel_minutes", 0) or 0) > radius_minutes:
        return False

    return True


def _initialize_discover_state() -> None:
    if "discover_query" not in st.session_state:
        st.session_state.discover_query = st.session_state.get("search_query", "")

    if "discover_categories" not in st.session_state:
        st.session_state.discover_categories = []

    if "discover_borough" not in st.session_state:
        st.session_state.discover_borough = "All"

    if "discover_prices" not in st.session_state:
        st.session_state.discover_prices = []

    if "discover_min_rating" not in st.session_state:
        st.session_state.discover_min_rating = 4.0

    if "discover_radius_minutes" not in st.session_state:
        st.session_state.discover_radius_minutes = 30

    if "discover_show_count" not in st.session_state:
        st.session_state.discover_show_count = 24

    if st.session_state.discover_show_count not in SHOW_OPTIONS:
        st.session_state.discover_show_count = 24


def _init_discover_view_state() -> None:
    """
    Track which restaurant cards have already been logged as viewed
    in the current app session, so we do not spam MongoDB on every rerun.
    """
    if "discover_viewed_ids" not in st.session_state:
        st.session_state.discover_viewed_ids = []


def _apply_pending_reset() -> None:
    if st.session_state.get("pending_discover_reset", False):
        st.session_state.discover_query = ""
        st.session_state.search_query = ""
        st.session_state.discover_categories = []
        st.session_state.discover_borough = "All"
        st.session_state.discover_prices = []
        st.session_state.discover_min_rating = 4.0
        st.session_state.discover_radius_minutes = 30
        st.session_state.pending_discover_reset = False


def _log_discover_views(restaurants: list[dict]) -> None:
    """
    Log 'viewed' interactions for restaurants currently rendered in Discover.
    Only logs for logged-in users and only once per business_id per session.
    """
    if not st.session_state.get("is_logged_in", False):
        return

    current_user = st.session_state.get("current_user", {})
    username = current_user.get("username", "")
    if not username:
        return

    already_logged = set(st.session_state.get("discover_viewed_ids", []))
    newly_logged: list[str] = []

    for item in restaurants:
        business_id = item.get("business_id")
        if not business_id:
            continue

        if business_id in already_logged:
            continue

        log_user_interaction(username, business_id, "viewed")
        newly_logged.append(business_id)

    if newly_logged:
        st.session_state.discover_viewed_ids = list(already_logged.union(newly_logged))


def render_discover(restaurants: list[dict]) -> None:
    """
    Render the Discover page with filters, map, and restaurant cards.
    """
    # Important: clear pending reset BEFORE any widget is created
    _apply_pending_reset()
    _initialize_discover_state()
    _init_discover_view_state()

    normalized = normalize_results(restaurants or [])
    filter_options = st.session_state.get("filter_options", {})

    # Keep borough state valid if available options changed
    borough_options = ["All"] + filter_options.get("boroughs", [])
    if st.session_state.discover_borough not in borough_options:
        st.session_state.discover_borough = "All"

    left, right = st.columns([1.02, 2.28], gap="large")

    with left:
        st.markdown("<div class='nb-panel-title'>Filters</div>", unsafe_allow_html=True)

        st.text_input(
            "Search",
            key="discover_query",
            placeholder="cheap spicy noodles near washington square",
        )
        st.session_state.search_query = st.session_state.discover_query

        render_location_picker()

        st.multiselect(
            "Cuisine",
            options=filter_options.get("categories", []),
            key="discover_categories",
        )

        st.selectbox(
            "Borough",
            options=borough_options,
            key="discover_borough",
        )

        st.multiselect(
            "Price",
            options=filter_options.get("prices", []),
            key="discover_prices",
        )

        st.slider(
            "Minimum rating",
            min_value=0.0,
            max_value=5.0,
            step=0.1,
            key="discover_min_rating",
        )

        st.slider(
            "Radius (minutes)",
            min_value=5,
            max_value=120,
            step=5,
            key="discover_radius_minutes",
        )

        if st.button("Clear filters", use_container_width=True):
            st.session_state.discover_query = ""
            st.session_state.search_query = ""
            st.session_state.discover_categories = []
            st.session_state.discover_borough = "All"
            st.session_state.discover_prices = []
            st.session_state.discover_min_rating = 4.0
            st.session_state.discover_radius_minutes = 30
            st.session_state.discover_viewed_ids = []
            st.rerun()

    current_user = st.session_state.get("current_user", {}) or {}
    user_id = current_user.get("username") or "anonymous"

    backend_filters = {
        "discover_categories": st.session_state.get("discover_categories", []),
        "discover_borough": st.session_state.get("discover_borough", "All"),
        "discover_prices": st.session_state.get("discover_prices", []),
        "discover_min_rating": float(st.session_state.get("discover_min_rating", 4.0)),
        "discover_radius_minutes": int(st.session_state.get("discover_radius_minutes", 30)),
    }

    backend_ranked = search_restaurants(
        query=st.session_state.get("discover_query", ""),
        filters=backend_filters,
        user_id=user_id,
        top_k=200,
        user_vector_only=False,
    )

    filtered = normalize_results(
        [
            {
                **item,
                "score": float(item.get("final_score", item.get("score", 0.0)) or 0.0),
            }
            for item in backend_ranked
        ]
    )

    jump_id = st.session_state.get("jump_to_business_id")
    if jump_id:
        jump_item = next(
            (item for item in normalized if item.get("business_id") == jump_id),
            None,
        )
        if jump_item:
            already_present = any(
                item.get("business_id") == jump_id
                for item in filtered
            )
            if not already_present:
                filtered = [jump_item] + filtered

    focus_id = st.session_state.get("focus_business_id")
    ordered = sort_results(filtered, focus_id)

    # Clear one-time jump after the list has been rebuilt
    if "jump_to_business_id" in st.session_state:
        del st.session_state["jump_to_business_id"]

    with right:
        toolbar_left, toolbar_right = st.columns([1.7, 1.0], gap="small")

        with toolbar_left:
            st.markdown(
                f"<div class='nb-panel-title'>Results · {len(ordered)} matches</div>",
                unsafe_allow_html=True,
            )

        with toolbar_right:
            st.selectbox(
                "Show",
                options=SHOW_OPTIONS,
                key="discover_show_count",
            )

        st.markdown("<div class='nb-section-title'>Map</div>", unsafe_allow_html=True)
        render_map(ordered[:80])

        st.markdown("<div class='nb-section-title'>Restaurants</div>", unsafe_allow_html=True)

        if not ordered:
            render_empty_state(
                "No matching restaurants",
                "Try widening the radius, lowering the rating threshold, or changing cuisines.",
            )
            return

        show_value = st.session_state.get("discover_show_count", 24)
        display_count = len(ordered) if show_value == "All" else int(show_value)
        visible_results = ordered[:display_count]

        # Only log what is actually shown on the page
        _log_discover_views(visible_results)

        cols = st.columns(2, gap="large")
        for idx, item in enumerate(visible_results):
            with cols[idx % 2]:
                render_restaurant_card(item, key_prefix=f"discover_{idx}")