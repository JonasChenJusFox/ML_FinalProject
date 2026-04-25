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
    focused = next((r for r in restaurants if r.get("business_id") == focus_id), restaurants[0])

    center_lat = focused.get("latitude", 40.73)
    center_lon = focused.get("longitude", -73.99)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)

    if focus_id:
        st.caption(f"Focused on: {focused.get('name', 'Selected restaurant')}")

    for item in restaurants:
        lat = item.get("latitude")
        lon = item.get("longitude")
        if not lat or not lon:
            continue

        business_id = item.get("business_id", "")
        name = item.get("name", "Restaurant")
        rating = float(item.get("rating", 0.0) or 0.0)
        is_focus = business_id == focus_id

        popup = f"{name} · ⭐ {rating:.1f}"

        if is_focus:
            folium.Marker(
                [lat, lon],
                popup=popup,
                tooltip=name,
                icon=folium.Icon(color="red", icon="cutlery", prefix="fa"),
            ).add_to(m)
        else:
            folium.Marker(
                [lat, lon],
                popup=popup,
                tooltip=name,
                icon=folium.Icon(color="orange", icon="cutlery", prefix="fa"),
            ).add_to(m)

    payload = st_folium(
        m,
        width=None,
        height=420,
        returned_objects=["last_object_clicked_popup"],
    )

    clicked = None
    if isinstance(payload, dict):
        clicked_popup = payload.get("last_object_clicked_popup")
        if isinstance(clicked_popup, str):
            clicked = clicked_popup.split(" · ⭐ ", 1)[0].strip()

    if clicked:
        clicked_restaurant = next(
            (item for item in restaurants if item.get("name") == clicked),
            None,
        )
        clicked_business_id = clicked_restaurant.get("business_id") if clicked_restaurant else None
    else:
        clicked_business_id = None

    if clicked_business_id and clicked_business_id != st.session_state.get("focus_business_id"):
        st.session_state.focus_business_id = clicked_business_id
        st.session_state.jump_to_business_id = clicked_business_id

        st.session_state.page = "Discover"
        st.rerun()
