"""
frontend/components/map_view.py
Owner: Jonas Chen

Responsibilities:
- Renders the interactive restaurant map
- Displays restaurant markers based on filtered results
- Highlights the currently focused restaurant
- Supports clicking map markers to reorder or refocus results
"""

from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium


def render_map(restaurants: list[dict]) -> None:
    if not restaurants:
        st.info("No restaurants to map.")
        return

    focus_id = st.session_state.get("focus_business_id")
    focused = next((r for r in restaurants if r["business_id"] == focus_id), restaurants[0])

    center_lat = focused.get("latitude", 40.73)
    center_lon = focused.get("longitude", -73.99)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)

    for item in restaurants:
        lat = item.get("latitude")
        lon = item.get("longitude")
        if not lat or not lon:
            continue

        is_focus = item["business_id"] == focus_id
        popup = f"{item['name']} · ⭐ {item.get('rating', 0.0):.1f}"

        if is_focus:
            folium.Marker(
                [lat, lon],
                popup=popup,
                tooltip=item["business_id"],
                icon=folium.Icon(color="red", icon="cutlery", prefix="fa"),
            ).add_to(m)
        else:
            folium.Marker(
                [lat, lon],
                popup=popup,
                tooltip=item["business_id"],
                icon=folium.Icon(color="orange", icon="cutlery", prefix="fa"),
            ).add_to(m)

    payload = st_folium(
        m,
        width=None,
        height=420,
        returned_objects=["last_object_clicked_tooltip"],
    )

    clicked = None
    if isinstance(payload, dict):
        clicked = payload.get("last_object_clicked_tooltip")

    if clicked and clicked != st.session_state.get("focus_business_id"):
        st.session_state.focus_business_id = clicked
        st.session_state.jump_to_business_id = clicked

        # Clear lingering search text
        st.session_state.discover_query = ""
        st.session_state.search_query = ""
        if "discover_query_input" in st.session_state:
            st.session_state.discover_query_input = ""

        st.session_state.page = "Discover"
        st.rerun()