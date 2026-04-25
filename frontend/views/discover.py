"""
frontend/views/discover.py
Owner: Jonas Chen

Responsibilities:
- Renders the main restaurant discovery page
- Keeps search query-first, with optional advanced filters
- Displays map results and restaurant cards
- Supports focus-map behavior and result reordering
- Provides clear feedback about current search/filter state
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import normalize_results, sort_results
from frontend.components.empty_state import render_empty_state
from frontend.components.location_picker import render_location_picker
from frontend.components.map_view import render_map
from frontend.components.restaurant_card import render_restaurant_card
from integration.api import search_restaurants

INITIAL_RESULT_COUNT = 12
RESULTS_INCREMENT = 12


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

    if "discover_visible_count" not in st.session_state:
        st.session_state.discover_visible_count = INITIAL_RESULT_COUNT

    if "discover_last_feedback" not in st.session_state:
        st.session_state.discover_last_feedback = ""


def _apply_pending_reset() -> None:
    if st.session_state.get("pending_discover_reset", False):
        st.session_state.discover_query = ""
        st.session_state.search_query = ""
        st.session_state.discover_categories = []
        st.session_state.discover_borough = "All"
        st.session_state.discover_prices = []
        st.session_state.discover_min_rating = 4.0
        st.session_state.discover_radius_minutes = 30
        st.session_state.discover_visible_count = INITIAL_RESULT_COUNT
        st.session_state.discover_last_feedback = "Filters cleared. Showing refreshed results."
        st.session_state.pending_discover_reset = False


def _active_filter_summary() -> list[str]:
    summary: list[str] = []
    if st.session_state.get("discover_categories"):
        summary.append(f"{len(st.session_state.get('discover_categories', []))} cuisine filter(s)")
    if st.session_state.get("discover_borough", "All") != "All":
        summary.append(f"borough: {st.session_state.get('discover_borough')}")
    if st.session_state.get("discover_prices"):
        summary.append(f"price: {', '.join(st.session_state.get('discover_prices', []))}")
    if float(st.session_state.get("discover_min_rating", 4.0)) != 4.0:
        summary.append(f"min rating: {float(st.session_state.get('discover_min_rating', 4.0)):.1f}+")
    if int(st.session_state.get("discover_radius_minutes", 30)) != 30:
        summary.append(f"radius: {int(st.session_state.get('discover_radius_minutes', 30))} min")
    return summary


def _run_search(user_id: str) -> list[dict]:
    backend_filters = {
        "discover_categories": st.session_state.get("discover_categories", []),
        "discover_borough": st.session_state.get("discover_borough", "All"),
        "discover_prices": st.session_state.get("discover_prices", []),
        "discover_min_rating": float(st.session_state.get("discover_min_rating", 4.0)),
        "discover_radius_minutes": int(st.session_state.get("discover_radius_minutes", 30)),
        "origin_lat": (
            float(st.session_state.get("user_lat"))
            if st.session_state.get("use_my_location", False)
            and st.session_state.get("user_lat") is not None
            else None
        ),
        "origin_lon": (
            float(st.session_state.get("user_lon"))
            if st.session_state.get("use_my_location", False)
            and st.session_state.get("user_lon") is not None
            else None
        ),
    }

    with st.spinner("Updating results..."):
        return search_restaurants(
            query=st.session_state.get("discover_query", ""),
            filters=backend_filters,
            user_id=user_id,
            top_k=200,
            user_vector_only=False,
        )


def render_discover(restaurants: list[dict]) -> None:
    _apply_pending_reset()
    _initialize_discover_state()

    normalized = normalize_results(restaurants or [])
    filter_options = st.session_state.get("filter_options", {})

    borough_options = ["All"] + filter_options.get("boroughs", [])
    if st.session_state.discover_borough not in borough_options:
        st.session_state.discover_borough = "All"

    st.markdown("### Discover")
    st.caption("Search first. Advanced filters are optional and only help narrow what you already asked for.")

    with st.form("discover_search_form", clear_on_submit=False):
        search_cols = st.columns([6.0, 1.0], gap="small")
        with search_cols[0]:
            query = st.text_input(
                "Search",
                key="discover_query",
                placeholder="cheap spicy noodles near washington square",
            )
            st.session_state.search_query = query
        with search_cols[1]:
            search_submitted = st.form_submit_button("Search", use_container_width=True)
        if search_submitted:
            st.session_state.discover_visible_count = INITIAL_RESULT_COUNT
            st.session_state.discover_last_feedback = "Results updated from your search."

    with st.expander("Advanced filters", expanded=False):
        render_location_picker()
        filter_cols_a = st.columns(2, gap="large")
        filter_cols_b = st.columns(2, gap="large")

        with filter_cols_a[0]:
            st.multiselect(
                "Cuisine",
                options=filter_options.get("categories", []),
                key="discover_categories",
            )
            st.multiselect(
                "Price",
                options=filter_options.get("prices", []),
                key="discover_prices",
            )

        with filter_cols_a[1]:
            st.selectbox(
                "Borough",
                options=borough_options,
                key="discover_borough",
            )
            st.slider(
                "Minimum rating",
                min_value=0.0,
                max_value=5.0,
                step=0.1,
                key="discover_min_rating",
            )

        with filter_cols_b[0]:
            st.slider(
                "Radius (minutes)",
                min_value=5,
                max_value=120,
                step=5,
                key="discover_radius_minutes",
            )

        with filter_cols_b[1]:
            if st.button("Clear filters", key="discover_clear_filters", use_container_width=True):
                st.session_state.pending_discover_reset = True
                st.rerun()

    active_filters = _active_filter_summary()
    if active_filters:
        st.info("Using your search plus filters: " + " • ".join(active_filters))
    else:
        st.info("Using your search and built-in query parsing. No manual filters are active.")

    feedback = st.session_state.get("discover_last_feedback", "")
    if feedback:
        st.success(feedback)
        st.session_state.discover_last_feedback = ""

    current_user = st.session_state.get("current_user", {}) or {}
    user_id = current_user.get("username") or "anonymous"
    backend_ranked = _run_search(user_id)

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
            already_present = any(item.get("business_id") == jump_id for item in filtered)
            if not already_present:
                filtered = [jump_item] + filtered

    focus_id = st.session_state.get("focus_business_id")
    ordered = sort_results(filtered, focus_id)

    if "jump_to_business_id" in st.session_state:
        del st.session_state["jump_to_business_id"]

    summary_cols = st.columns([1.5, 1.2, 1.3], gap="small")
    summary_cols[0].markdown(
        f"<div class='nb-panel-title'>Results · {len(ordered)} relevant places</div>",
        unsafe_allow_html=True,
    )
    summary_cols[1].caption(
        "Focused restaurant pinned first on the map and list."
        if focus_id
        else "Use Focus on map from a card to pin a place."
    )
    summary_cols[2].caption(
        "Showing the first "
        f"{min(len(ordered), int(st.session_state.get('discover_visible_count', INITIAL_RESULT_COUNT)))} results."
    )

    st.markdown("<div class='nb-section-title'>Map</div>", unsafe_allow_html=True)
    render_map(ordered[:80])

    st.markdown("<div class='nb-section-title'>Restaurants</div>", unsafe_allow_html=True)

    if not ordered:
        render_empty_state(
            "No matching restaurants",
            "Try a broader query or relax your advanced filters.",
        )
        return

    visible_count = int(st.session_state.get("discover_visible_count", INITIAL_RESULT_COUNT))
    visible_results = ordered[:visible_count]

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(visible_results):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"discover_{idx}")

    if len(visible_results) < len(ordered):
        if st.button("Show more", key="discover_show_more", use_container_width=True):
            st.session_state.discover_visible_count = min(
                len(ordered),
                visible_count + RESULTS_INCREMENT,
            )
            st.rerun()
