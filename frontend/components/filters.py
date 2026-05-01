"""Sidebar filter widgets (cuisine, borough, price, rating, radius, sort) in session state."""

from __future__ import annotations

import streamlit as st


from frontend.state import DEFAULT_FILTERS


SORT_OPTIONS = ["Relevance", "Highest rated", "Closest", "Lowest price"]


def render_filters(options: dict) -> dict:
    current = st.session_state.get("filters", DEFAULT_FILTERS.copy())

    st.markdown("<div class='nb-panel-title'>Filters</div>", unsafe_allow_html=True)
    selected_cuisines = st.multiselect(
        "Cuisine",
        options=options.get("cuisines", []),
        default=current.get("cuisines", []),
        placeholder="All cuisines",
    )

    price_choices = {1: "$", 2: "$$", 3: "$$$", 4: "$$$$", 5: "$$$$$"}
    selected_price_labels = st.multiselect(
        "Price",
        options=list(price_choices.values()),
        default=[price_choices[item] for item in current.get("price_levels", []) if item in price_choices],
        placeholder="All price levels",
    )
    selected_price_levels = [level for level, label in price_choices.items() if label in selected_price_labels]

    min_rating = st.selectbox(
        "Minimum rating",
        options=[0.0, 4.0, 4.2, 4.5, 4.7],
        index=[0.0, 4.0, 4.2, 4.5, 4.7].index(float(current.get("min_rating", 0.0))),
        format_func=lambda value: "Any rating" if value == 0.0 else f"{value:.1f}+",
    )

    borough_options = ["All"] + options.get("boroughs", [])
    borough = st.selectbox(
        "Borough",
        options=borough_options,
        index=borough_options.index(current.get("borough", "All")) if current.get("borough", "All") in borough_options else 0,
    )

    travel_radius_min = st.slider(
        "Travel radius from NYU (minutes)",
        min_value=10,
        max_value=90,
        step=5,
        value=int(current.get("travel_radius_min", 30)),
    )

    sort_by = st.selectbox(
        "Sort by",
        options=SORT_OPTIONS,
        index=SORT_OPTIONS.index(current.get("sort_by", "Relevance")) if current.get("sort_by", "Relevance") in SORT_OPTIONS else 0,
    )

    filters = {
        "cuisines": selected_cuisines,
        "price_levels": selected_price_levels,
        "min_rating": min_rating,
        "borough": borough,
        "travel_radius_min": travel_radius_min,
        "sort_by": sort_by,
    }
    st.session_state.filters = filters
    return filters