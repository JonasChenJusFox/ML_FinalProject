"""
frontend/ui.py
Owner: Jonas (+ Fidaa for design)

Responsibilities:
- Render the Streamlit search bar
- Render the sidebar filter UI
- Display restaurant result cards with images
- Render the map view of results
"""

import streamlit as st


def render_search_bar() -> str:
    """
    Render the main semantic search input.

    Returns:
        The user's query string (empty string if nothing typed).
    """
    query = st.text_input(
        label="What are you looking for?",
        placeholder='e.g. "cheap spicy ramen near NYU" or "cozy date night spot in the East Village"',
    )
    return query


def render_filters() -> dict:
    """
    Render the sidebar filter panel.

    Returns:
        Dict of active filter values.
    """
    with st.sidebar:
        st.header("Filters")

        # TODO (Jonas): implement filter UI widgets
        # Placeholder — returns empty filters so app doesn't crash
        filters = {
            "price": [],
            "cuisines": [],
            "min_rating": 0.0,
            "open_now": False,
            "dietary": [],
            "neighborhood": "",
            "max_distance_km": 5.0,
            "pet_friendly": False,
            "kid_friendly": False,
            "accessible": False,
        }

    return filters


def render_results(restaurants: list[dict]) -> None:
    """
    Render the ranked list of restaurant result cards.

    Args:
        restaurants: Ordered list of restaurant dicts from the ranker.
    """
    if not restaurants:
        st.warning("No restaurants found. Try a different query or adjust your filters.")
        return

    st.markdown(f"**{len(restaurants)} results found**")

    # TODO (Jonas): replace with rich card layout + map view
    for r in restaurants:
        st.write(r.get("name", "Unknown"))
