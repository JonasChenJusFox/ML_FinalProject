"""
frontend/views/discover.py
Owner: Jonas Chen

Responsibilities:
- Renders the main restaurant discovery page
- Shows only the current-origin summary below the search bar
- Keeps full location controls inside the optional filter panel
- Shows the map above the filter / restaurant layout
- Displays paginated restaurant cards with optional inline filters
"""

from __future__ import annotations

import math

import streamlit as st

from frontend.adapters import clean_text, normalize_results
from frontend.components.empty_state import render_empty_state
from frontend.components.location_picker import (
    apply_location_draft,
    render_location_controls,
    render_location_summary,
    reset_location_selection,
)
from frontend.components.map_view import render_map
from frontend.components.restaurant_card import render_restaurant_card
from frontend.components.search_bar import DISCOVER_PLACEHOLDER, render_search_bar
from frontend.location_utils import matches_location_filter
from integration.api import search_restaurants
from integration.db import log_user_interaction

RESULTS_PER_PAGE = 20
RATING_OPTIONS: list[tuple[str, float]] = [
    ("Any rating", 0.0),
    ("4.0+", 4.0),
    ("4.3+", 4.3),
    ("4.5+", 4.5),
    ("4.7+", 4.7),
]
RADIUS_OPTIONS: list[tuple[str, int | None]] = [
    ("Any distance", None),
    ("10 min", 10),
    ("20 min", 20),
    ("30 min", 30),
    ("45 min", 45),
    ("60 min", 60),
]


def _initialize_discover_state() -> None:
    if "discover_query" not in st.session_state:
        st.session_state.discover_query = st.session_state.get("search_query", "")
    if "discover_active_query" not in st.session_state:
        st.session_state.discover_active_query = st.session_state.get("search_query", "")
    if "discover_categories" not in st.session_state:
        st.session_state.discover_categories = []
    if "discover_borough" not in st.session_state:
        st.session_state.discover_borough = "All"
    if "discover_prices" not in st.session_state:
        st.session_state.discover_prices = []
    if "discover_min_rating" not in st.session_state:
        st.session_state.discover_min_rating = 0.0
    if "discover_radius_minutes" not in st.session_state:
        st.session_state.discover_radius_minutes = None
    if "discover_filters_open" not in st.session_state:
        st.session_state.discover_filters_open = False
    if "discover_filters_enabled" not in st.session_state:
        st.session_state.discover_filters_enabled = False
    if "discover_categories_draft" not in st.session_state:
        st.session_state.discover_categories_draft = list(st.session_state.get("discover_categories", []))
    if "discover_borough_draft" not in st.session_state:
        st.session_state.discover_borough_draft = st.session_state.get("discover_borough", "All")
    if "discover_prices_draft" not in st.session_state:
        st.session_state.discover_prices_draft = list(st.session_state.get("discover_prices", []))
    if "discover_min_rating_draft" not in st.session_state:
        st.session_state.discover_min_rating_draft = float(st.session_state.get("discover_min_rating", 0.0) or 0.0)
    if "discover_radius_minutes_draft" not in st.session_state:
        st.session_state.discover_radius_minutes_draft = st.session_state.get("discover_radius_minutes")
    if "discover_rating_label_draft" not in st.session_state:
        st.session_state.discover_rating_label_draft = next(
            (label for label, value in RATING_OPTIONS if value == st.session_state.discover_min_rating_draft),
            "Any rating",
        )
    if "discover_radius_label_draft" not in st.session_state:
        st.session_state.discover_radius_label_draft = next(
            (label for label, value in RADIUS_OPTIONS if value == st.session_state.discover_radius_minutes_draft),
            "Any distance",
        )
    if "discover_reset_drafts" not in st.session_state:
        st.session_state.discover_reset_drafts = False
    if "discover_page" not in st.session_state:
        st.session_state.discover_page = 1
    if "discover_last_signature" not in st.session_state:
        st.session_state.discover_last_signature = None
    if "discover_viewed_ids" not in st.session_state:
        st.session_state.discover_viewed_ids = []


def _clear_discover_filters() -> None:
    st.session_state.discover_categories = []
    st.session_state.discover_borough = "All"
    st.session_state.discover_prices = []
    st.session_state.discover_min_rating = 0.0
    st.session_state.discover_radius_minutes = None
    st.session_state.discover_filters_enabled = False
    st.session_state.discover_reset_drafts = True
    st.session_state.discover_page = 1
    reset_location_selection()


def _sync_filter_draft_state() -> None:
    if not st.session_state.get("discover_reset_drafts", False):
        return

    st.session_state.discover_categories_draft = list(st.session_state.get("discover_categories", []))
    st.session_state.discover_borough_draft = st.session_state.get("discover_borough", "All")
    st.session_state.discover_prices_draft = list(st.session_state.get("discover_prices", []))
    st.session_state.discover_min_rating_draft = float(st.session_state.get("discover_min_rating", 0.0) or 0.0)
    st.session_state.discover_radius_minutes_draft = st.session_state.get("discover_radius_minutes")
    st.session_state.discover_rating_label_draft = next(
        (label for label, value in RATING_OPTIONS if value == st.session_state.discover_min_rating_draft),
        "Any rating",
    )
    st.session_state.discover_radius_label_draft = next(
        (label for label, value in RADIUS_OPTIONS if value == st.session_state.discover_radius_minutes_draft),
        "Any distance",
    )
    st.session_state.discover_reset_drafts = False


def _log_discover_views(restaurants: list[dict]) -> None:
    if not st.session_state.get("is_logged_in", False):
        return

    current_user = st.session_state.get("current_user", {}) or {}
    username = current_user.get("username", "")
    if not username:
        return

    already_logged = set(st.session_state.get("discover_viewed_ids", []))
    newly_logged: list[str] = []

    for item in restaurants:
        business_id = item.get("business_id")
        if not business_id or business_id in already_logged:
            continue
        log_user_interaction(username, business_id, "viewed")
        newly_logged.append(business_id)

    if newly_logged:
        st.session_state.discover_viewed_ids = list(already_logged.union(newly_logged))


def _current_signature() -> tuple:
    return (
        clean_text(st.session_state.get("discover_active_query", "")).lower(),
        bool(st.session_state.get("discover_filters_enabled", False)),
        tuple(sorted(st.session_state.get("discover_categories", []) or [])),
        clean_text(st.session_state.get("discover_borough", "All")),
        tuple(sorted(st.session_state.get("discover_prices", []) or [])),
        float(st.session_state.get("discover_min_rating", 0.0) or 0.0),
        st.session_state.get("discover_radius_minutes"),
        bool(st.session_state.get("use_my_location", False)),
        clean_text(st.session_state.get("selected_zipcode", "")),
        st.session_state.get("user_lat"),
        st.session_state.get("user_lon"),
    )


def _sync_pagination_signature() -> None:
    signature = _current_signature()
    if st.session_state.get("discover_last_signature") != signature:
        st.session_state.discover_page = 1
        st.session_state.discover_last_signature = signature


def _commit_discover_search() -> None:
    committed_query = clean_text(st.session_state.get("discover_query", ""))
    st.session_state.discover_active_query = committed_query
    st.session_state.search_query = committed_query
    st.session_state.discover_page = 1


def _render_filter_panel(filter_options: dict, restaurants: list[dict]) -> None:
    _sync_filter_draft_state()

    st.markdown("<div class='nb-panel-title'>Filters</div>", unsafe_allow_html=True)
    st.markdown("<div class='nb-discover-filter-anchor'></div>", unsafe_allow_html=True)
    filter_mode = "On" if st.session_state.get("discover_filters_enabled", False) else "Off"
    st.markdown(
        "<div class='nb-filter-feedback nb-filter-feedback-on'>"
        "<span class='nb-filter-feedback-label'>Filter mode</span>"
        f"<span class='nb-filter-feedback-value'>{filter_mode}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    render_location_controls(restaurants)

    borough_options = ["All"] + filter_options.get("boroughs", [])
    if st.session_state.get("discover_borough_draft") not in borough_options:
        st.session_state.discover_borough_draft = "All"

    rating_lookup = {value: label for label, value in RATING_OPTIONS}
    current_rating = float(st.session_state.get("discover_min_rating_draft", 0.0) or 0.0)
    rating_label = rating_lookup.get(current_rating, "Any rating")

    radius_lookup = {label: value for label, value in RADIUS_OPTIONS}
    current_radius = st.session_state.get("discover_radius_minutes_draft")
    radius_label = next(
        (label for label, value in RADIUS_OPTIONS if value == current_radius),
        "Any distance",
    )

    price_options = filter_options.get("prices", [])
    current_prices = st.session_state.get("discover_prices_draft", [])
    price_defaults = [
        price
        for price in current_prices
        if price in price_options
    ]
    st.session_state.discover_prices_draft = price_defaults

    st.multiselect(
        "Cuisine",
        options=filter_options.get("categories", []),
        key="discover_categories_draft",
        placeholder="Choose cuisines",
    )
    st.selectbox(
        "Borough",
        options=borough_options,
        key="discover_borough_draft",
    )
    st.multiselect(
        "Price",
        options=price_options,
        key="discover_prices_draft",
        placeholder="Choose price levels",
    )
    st.selectbox(
        "Travel time from current origin",
        options=[label for label, _ in RADIUS_OPTIONS],
        key="discover_radius_label_draft",
    )
    st.selectbox(
        "Minimum rating",
        options=[label for label, _ in RATING_OPTIONS],
        key="discover_rating_label_draft",
    )

    action_cols = st.columns(2, gap="small")
    clear_submitted = action_cols[0].button("Clear filters", key="discover_clear_filters", use_container_width=True)
    apply_submitted = action_cols[1].button("Apply filters", key="discover_apply_filters", use_container_width=True)

    if clear_submitted:
        _clear_discover_filters()
        st.rerun()

    if apply_submitted:
        selected_categories = list(st.session_state.get("discover_categories_draft", []) or [])
        selected_borough = st.session_state.get("discover_borough_draft", "All")
        selected_prices = list(st.session_state.get("discover_prices_draft", []) or [])
        selected_radius = st.session_state.get("discover_radius_label_draft", radius_label)
        selected_rating = st.session_state.get("discover_rating_label_draft", rating_label)

        location_valid, _ = apply_location_draft(restaurants)
        if not location_valid:
            return

        st.session_state.discover_categories = selected_categories
        st.session_state.discover_borough = selected_borough
        st.session_state.discover_prices = selected_prices
        st.session_state.discover_min_rating = dict(RATING_OPTIONS)[selected_rating]
        st.session_state.discover_radius_minutes = radius_lookup[selected_radius]
        st.session_state.discover_page = 1
        st.session_state.discover_filters_enabled = True
        st.session_state.discover_reset_drafts = True
        st.rerun()


def _apply_frontend_filters(restaurants: list[dict]) -> list[dict]:
    if not st.session_state.get("discover_filters_enabled", False):
        return restaurants

    selected_categories = st.session_state.get("discover_categories", []) or []
    selected_prices = st.session_state.get("discover_prices", []) or []
    selected_borough = st.session_state.get("discover_borough", "All")
    min_rating = float(st.session_state.get("discover_min_rating", 0.0) or 0.0)
    max_minutes = st.session_state.get("discover_radius_minutes")

    filtered: list[dict] = []
    for item in restaurants:
        categories = item.get("categories", []) or []
        if selected_categories and not any(category in categories for category in selected_categories):
            continue

        price_text = clean_text(item.get("price_display") or item.get("price") or "")
        if selected_prices and price_text not in selected_prices:
            continue

        rating = float(item.get("rating", 0.0) or 0.0)
        if rating < min_rating:
            continue

        if not matches_location_filter(item, selected_borough):
            continue

        if max_minutes is not None:
            travel_minutes = int(item.get("travel_minutes", 0) or 0)
            if not travel_minutes or travel_minutes > int(max_minutes):
                continue

        filtered.append(item)

    return filtered


def _render_pagination(total_items: int, position: str) -> tuple[int, int]:
    total_pages = max(1, math.ceil(total_items / RESULTS_PER_PAGE))
    current_page = int(st.session_state.get("discover_page", 1) or 1)
    current_page = max(1, min(current_page, total_pages))
    st.session_state.discover_page = current_page

    left, middle, right = st.columns([1.2, 2.4, 1.2], gap="small")
    with left:
        if st.button(
            "Previous",
            key=f"discover_prev_{position}_{current_page}",
            use_container_width=True,
            disabled=current_page <= 1,
        ):
            st.session_state.discover_page = current_page - 1
            st.rerun()

    with middle:
        st.markdown(
            f"<div class='nb-panel-title' style='text-align:center;'>Page {current_page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with right:
        if st.button(
            "Next",
            key=f"discover_next_{position}_{current_page}",
            use_container_width=True,
            disabled=current_page >= total_pages,
        ):
            st.session_state.discover_page = current_page + 1
            st.rerun()

    start = (current_page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    return start, end


def _sort_discover_results(
    restaurants: list[dict],
    active_query: str,
    focus_business_id: str | None = None,
) -> list[dict]:
    normalized = normalize_results(restaurants)
    use_origin_sort = bool(st.session_state.get("use_my_location", False)) and not clean_text(active_query)

    def sort_key(item: dict) -> tuple:
        focused_rank = 0 if focus_business_id and item.get("business_id") == focus_business_id else 1

        if use_origin_sort:
            travel_minutes = int(item.get("travel_minutes", 0) or 0)
            missing_travel = 1 if travel_minutes <= 0 else 0
            return (
                focused_rank,
                missing_travel,
                travel_minutes if travel_minutes > 0 else 10_000,
                -(item.get("rating", 0.0) or 0.0),
                -(item.get("score", 0.0) or 0.0),
                item.get("name", ""),
            )

        return (
            focused_rank,
            -(item.get("score", 0.0) or 0.0),
            -(item.get("rating", 0.0) or 0.0),
            item.get("name", ""),
        )

    return sorted(normalized, key=sort_key)


def _render_results_grid(restaurants: list[dict], start_index: int) -> None:
    _log_discover_views(restaurants)
    cols = st.columns(2, gap="large")
    for idx, item in enumerate(restaurants):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"discover_{start_index + idx}")


def render_discover(restaurants: list[dict]) -> None:
    _initialize_discover_state()

    normalized = normalize_results(restaurants or [])
    filter_options = st.session_state.get("filter_options", {})

    search_cols = st.columns([6.0, 1.0], gap="small")
    with search_cols[0]:
        render_search_bar(
            key="discover_query",
            placeholder=DISCOVER_PLACEHOLDER,
            on_change=_commit_discover_search,
        )
    with search_cols[1]:
        if st.button("Search", key="discover_search_button", use_container_width=True):
            _commit_discover_search()
            st.rerun()

    render_location_summary()
    _sync_pagination_signature()
    filters_enabled = bool(st.session_state.get("discover_filters_enabled", False))

    backend_filters = {
        "discover_categories": st.session_state.get("discover_categories", []) if filters_enabled else [],
        "discover_borough": st.session_state.get("discover_borough", "All") if filters_enabled else "All",
        "discover_prices": st.session_state.get("discover_prices", []) if filters_enabled else [],
        "discover_min_rating": float(st.session_state.get("discover_min_rating", 0.0) or 0.0) if filters_enabled else 0.0,
        "discover_radius_minutes": st.session_state.get("discover_radius_minutes") if filters_enabled else None,
    }

    active_query = clean_text(st.session_state.get("discover_active_query", ""))
    current_user = st.session_state.get("current_user", {}) or {}
    user_id = current_user.get("username") or "anonymous"

    backend_ranked = search_restaurants(
        query=active_query,
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
    filtered = _apply_frontend_filters(filtered)

    jump_id = st.session_state.get("jump_to_business_id")
    if jump_id:
        jump_item = next(
            (item for item in normalized if item.get("business_id") == jump_id),
            None,
        )
        if jump_item and not any(item.get("business_id") == jump_id for item in filtered):
            filtered = [jump_item] + filtered

    focus_id = st.session_state.get("focus_business_id")
    ordered = _sort_discover_results(filtered, active_query, focus_id)

    if "jump_to_business_id" in st.session_state:
        del st.session_state["jump_to_business_id"]

    st.markdown("<div class='nb-section-title'>Map</div>", unsafe_allow_html=True)
    map_results = ordered[:RESULTS_PER_PAGE] if ordered else []
    render_map(map_results)

    toggle_label = "Activate filters" if not st.session_state.get("discover_filters_open", False) else "Deactivate filters"
    if st.button(toggle_label, key="discover_toggle_filters", use_container_width=True):
        if st.session_state.get("discover_filters_open", False):
            _clear_discover_filters()
            st.session_state.discover_filters_open = False
        else:
            st.session_state.discover_filters_open = True
        st.rerun()

    if not ordered:
        render_empty_state(
            "No matching restaurants",
            "Try a different neighborhood, cuisine, or broader search phrase.",
        )
        return

    if st.session_state.get("discover_filters_open", False):
        filter_col, results_col = st.columns([1.05, 1.95], gap="large")
        with filter_col:
            _render_filter_panel(filter_options, normalized)
        with results_col:
            st.markdown("<div class='nb-section-title'>Restaurants</div>", unsafe_allow_html=True)
            start, end = _render_pagination(len(ordered), position="top")
            visible_results = ordered[start:end]
            _render_results_grid(visible_results, start)
            if len(ordered) > RESULTS_PER_PAGE:
                _render_pagination(len(ordered), position="bottom")
    else:
        st.markdown("<div class='nb-section-title'>Restaurants</div>", unsafe_allow_html=True)
        start, end = _render_pagination(len(ordered), position="top")
        visible_results = ordered[start:end]
        _render_results_grid(visible_results, start)
        if len(ordered) > RESULTS_PER_PAGE:
            _render_pagination(len(ordered), position="bottom")
