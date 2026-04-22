"""
frontend/views/discover.py
Owner: Jonas Chen

Responsibilities:
- Renders the main restaurant discovery page
- Keeps the page search-first, with filters hidden behind a toggle
- Displays a paginated map and restaurant card list
- Logs viewed restaurant cards for wrapped-style personalization
"""

from __future__ import annotations

import math

import streamlit as st

from frontend.adapters import clean_text, get_current_origin_kwargs, normalize_results, sort_results
from frontend.components.empty_state import render_empty_state
from frontend.components.location_picker import render_location_picker
from frontend.components.map_view import render_map
from frontend.components.restaurant_card import render_restaurant_card
from frontend.components.search_bar import DISCOVER_PLACEHOLDER, render_search_bar
from integration.api import search_restaurants
from integration.wrapped_repo import log_user_interaction

RESULTS_PER_PAGE = 20
ALL_PRICE_OPTION = "All price"
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
    elif float(st.session_state.get("discover_min_rating", 0.0) or 0.0) not in {
        value for _, value in RATING_OPTIONS
    }:
        st.session_state.discover_min_rating = 0.0

    if "discover_radius_minutes" not in st.session_state:
        st.session_state.discover_radius_minutes = None
    elif st.session_state.get("discover_radius_minutes") not in {
        value for _, value in RADIUS_OPTIONS
    }:
        st.session_state.discover_radius_minutes = None

    if "discover_filters_open" not in st.session_state:
        st.session_state.discover_filters_open = False

    if "discover_page" not in st.session_state:
        st.session_state.discover_page = 1

    if "discover_last_signature" not in st.session_state:
        st.session_state.discover_last_signature = None


def _init_discover_view_state() -> None:
    if "discover_viewed_ids" not in st.session_state:
        st.session_state.discover_viewed_ids = []


def _clear_discover_filters() -> None:
    st.session_state.discover_categories = []
    st.session_state.discover_borough = "All"
    st.session_state.discover_prices = []
    st.session_state.discover_min_rating = 0.0
    st.session_state.discover_radius_minutes = None
    st.session_state.discover_page = 1


def _log_discover_views(restaurants: list[dict]) -> None:
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
        if not business_id or business_id in already_logged:
            continue

        log_user_interaction(username, business_id, "viewed")
        newly_logged.append(business_id)

    if newly_logged:
        st.session_state.discover_viewed_ids = list(already_logged.union(newly_logged))


def _current_signature(origin_kwargs: dict) -> tuple:
    return (
        str(st.session_state.get("discover_active_query", "")).strip().lower(),
        tuple(sorted(st.session_state.get("discover_categories", []))),
        st.session_state.get("discover_borough", "All"),
        tuple(sorted(st.session_state.get("discover_prices", []))),
        float(st.session_state.get("discover_min_rating", 0.0) or 0.0),
        st.session_state.get("discover_radius_minutes"),
        round(float(origin_kwargs.get("origin_lat") or 0.0), 4),
        round(float(origin_kwargs.get("origin_lon") or 0.0), 4),
    )


def _sync_pagination_signature(origin_kwargs: dict) -> None:
    signature = _current_signature(origin_kwargs)
    if st.session_state.get("discover_last_signature") != signature:
        st.session_state.discover_page = 1
        st.session_state.discover_last_signature = signature


def _render_filter_panel(filter_options: dict) -> None:
    st.markdown("<div class='nb-panel-title'>Filters</div>", unsafe_allow_html=True)
    render_location_picker()
    st.markdown("<div class='nb-discover-filter-anchor'></div>", unsafe_allow_html=True)

    borough_options = ["All"] + filter_options.get("boroughs", [])
    if st.session_state.get("discover_borough") not in borough_options:
        st.session_state.discover_borough = "All"

    rating_lookup = {value: label for label, value in RATING_OPTIONS}
    current_rating = float(st.session_state.get("discover_min_rating", 0.0) or 0.0)
    rating_label = rating_lookup.get(current_rating, "Any rating")

    radius_lookup = {label: value for label, value in RADIUS_OPTIONS}
    current_radius = st.session_state.get("discover_radius_minutes")
    radius_label = next(
        (label for label, value in RADIUS_OPTIONS if value == current_radius),
        "Any distance",
    )
    price_options = [ALL_PRICE_OPTION] + filter_options.get("prices", [])
    current_prices = st.session_state.get("discover_prices", [])
    price_defaults = [
        price for price in current_prices
        if price in price_options and price != ALL_PRICE_OPTION
    ] or [ALL_PRICE_OPTION]

    with st.form("discover_filter_form"):
        left, right = st.columns(2, gap="large")
        with left:
            selected_categories = st.multiselect(
                "Cuisine",
                options=filter_options.get("categories", []),
                default=st.session_state.get("discover_categories", []),
                placeholder="Choose cuisines",
            )
            selected_prices = st.multiselect(
                "Price",
                options=price_options,
                default=price_defaults,
                placeholder="Choose price levels",
            )
            selected_rating = st.selectbox(
                "Minimum rating",
                options=[label for label, _ in RATING_OPTIONS],
                index=[label for label, _ in RATING_OPTIONS].index(rating_label),
            )

        with right:
            selected_borough = st.selectbox(
                "Borough",
                options=borough_options,
                index=borough_options.index(st.session_state.get("discover_borough", "All")),
            )
            selected_radius = st.selectbox(
                "Travel time from current origin",
                options=[label for label, _ in RADIUS_OPTIONS],
                index=[label for label, _ in RADIUS_OPTIONS].index(radius_label),
            )
            st.write("")

        footer_left, footer_right = st.columns(2, gap="large")
        with footer_left:
            clear_submitted = st.form_submit_button(
                "Clear filters",
                use_container_width=True,
            )
        with footer_right:
            apply_submitted = st.form_submit_button(
                "Apply filters",
                use_container_width=True,
            )

    if clear_submitted:
        _clear_discover_filters()
        st.session_state.discover_filters_open = False
        st.rerun()

    if apply_submitted:
        normalized_prices = [
            price for price in selected_prices
            if price != ALL_PRICE_OPTION
        ]
        if ALL_PRICE_OPTION in selected_prices:
            normalized_prices = []

        st.session_state.discover_categories = selected_categories
        st.session_state.discover_prices = normalized_prices
        st.session_state.discover_borough = selected_borough
        st.session_state.discover_min_rating = dict(RATING_OPTIONS)[selected_rating]
        st.session_state.discover_radius_minutes = radius_lookup[selected_radius]
        st.session_state.discover_page = 1
        st.session_state.discover_filters_open = False
        st.rerun()


def _render_filter_modal(filter_options: dict) -> None:
    if not st.session_state.get("discover_filters_open", False):
        return

    if any(
        [
            st.session_state.get("show_login_modal", False),
            st.session_state.get("show_signup_modal", False),
            st.session_state.get("show_forgot_password_modal", False),
            st.session_state.get("show_account_security_modal", False),
            st.session_state.get("show_questionnaire_modal", False),
            st.session_state.get("show_comments_modal", False),
        ]
    ):
        st.session_state.discover_filters_open = False
        return

    @st.dialog("Filters")
    def _dialog() -> None:
        _render_filter_panel(filter_options)

    _dialog()
    st.session_state.discover_filters_open = False


def _render_pagination(total_items: int, position: str) -> tuple[int, int]:
    total_pages = max(1, math.ceil(total_items / RESULTS_PER_PAGE))
    current_page = int(st.session_state.get("discover_page", 1) or 1)
    current_page = max(1, min(current_page, total_pages))
    st.session_state.discover_page = current_page

    left, middle, right = st.columns([1.2, 2.4, 1.2], gap="small")
    with left:
        previous_disabled = current_page <= 1
        if st.button(
            "Previous",
            key=f"discover_prev_{position}_{current_page}",
            use_container_width=True,
            disabled=previous_disabled,
        ):
            st.session_state.discover_page = current_page - 1
            st.rerun()

    with middle:
        st.markdown(
            f"<div class='nb-panel-title' style='text-align:center;'>Page {current_page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with right:
        next_disabled = current_page >= total_pages
        if st.button(
            "Next",
            key=f"discover_next_{position}_{current_page}",
            use_container_width=True,
            disabled=next_disabled,
        ):
            st.session_state.discover_page = current_page + 1
            st.rerun()

    start = (current_page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    return start, end


def render_discover(restaurants: list[dict]) -> None:
    _initialize_discover_state()
    _init_discover_view_state()

    normalized = normalize_results(restaurants or [])
    filter_options = st.session_state.get("filter_options", {})

    search_cols = st.columns([6.0, 1.0], gap="small")
    with search_cols[0]:
        query_text = render_search_bar(
            key="discover_query",
            placeholder=DISCOVER_PLACEHOLDER,
        )
    with search_cols[1]:
        if st.button("Search", key="discover_search_button", use_container_width=True):
            committed_query = clean_text(st.session_state.get("discover_query", ""))
            st.session_state.discover_active_query = committed_query
            st.session_state.search_query = committed_query
            st.session_state.discover_page = 1
            st.rerun()

    active_query = clean_text(st.session_state.get("discover_active_query", ""))

    if st.button("Open filters", key="discover_toggle_filters", use_container_width=True):
        st.session_state.discover_filters_open = True
        st.rerun()

    _render_filter_modal(filter_options)

    origin_kwargs = get_current_origin_kwargs()
    _sync_pagination_signature(origin_kwargs)

    backend_filters = {
        "discover_categories": st.session_state.get("discover_categories", []),
        "discover_borough": st.session_state.get("discover_borough", "All"),
        "discover_prices": st.session_state.get("discover_prices", []),
        "discover_min_rating": float(st.session_state.get("discover_min_rating", 0.0) or 0.0),
        "discover_radius_minutes": st.session_state.get("discover_radius_minutes"),
    }

    current_user = st.session_state.get("current_user", {}) or {}
    user_id = current_user.get("username") or "anonymous"

    backend_ranked = search_restaurants(
        query=active_query,
        filters=backend_filters,
        user_id=user_id,
        top_k=200,
        user_vector_only=False,
        **origin_kwargs,
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
        if jump_item and not any(item.get("business_id") == jump_id for item in filtered):
            filtered = [jump_item] + filtered

    focus_id = st.session_state.get("focus_business_id")
    ordered = sort_results(filtered, focus_id)

    if "jump_to_business_id" in st.session_state:
        del st.session_state["jump_to_business_id"]

    st.markdown("<div class='nb-panel-title'>Results</div>", unsafe_allow_html=True)

    if not ordered:
        render_empty_state(
            "No matching restaurants",
            "Try a different neighborhood, cuisine, or broader search phrase.",
        )
        return

    start, end = _render_pagination(len(ordered), position="top")
    visible_results = ordered[start:end]

    st.markdown("<div class='nb-section-title'>Map</div>", unsafe_allow_html=True)
    render_map(visible_results)

    st.markdown("<div class='nb-section-title'>Restaurants</div>", unsafe_allow_html=True)

    _log_discover_views(visible_results)

    cols = st.columns(2, gap="large")
    for idx, item in enumerate(visible_results):
        with cols[idx % 2]:
            render_restaurant_card(item, key_prefix=f"discover_{start + idx}")

    if len(ordered) > RESULTS_PER_PAGE:
        _render_pagination(len(ordered), position="bottom")
