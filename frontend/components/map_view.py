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

from frontend.adapters import get_current_origin


def _resolve_clicked_business_id(restaurants: list[dict], payload: dict) -> str | None:
    if payload.get("last_object_clicked_tooltip") == "Current origin":
        return None

    clicked = payload.get("last_object_clicked")
    if not isinstance(clicked, dict):
        return None

    try:
        clicked_lat = float(clicked.get("lat"))
        clicked_lng = float(clicked.get("lng"))
    except (TypeError, ValueError):
        return None

    best_id = None
    best_distance = None
    for item in restaurants:
        lat = item.get("latitude")
        lon = item.get("longitude")
        business_id = item.get("business_id")
        if lat in [None, ""] or lon in [None, ""] or not business_id:
            continue
        distance = abs(float(lat) - clicked_lat) + abs(float(lon) - clicked_lng)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_id = business_id

    if best_distance is not None and best_distance < 0.0005:
        return best_id
    return None


def render_map(restaurants: list[dict]) -> None:
    if not restaurants:
        st.info("No restaurants to map.")
        return

    focus_id = st.session_state.get("focus_business_id")
    focused = next((r for r in restaurants if r.get("business_id") == focus_id), restaurants[0])
    origin = get_current_origin()

    center_lat = origin.get("lat") if origin.get("lat") is not None else focused.get("latitude", 40.73)
    center_lon = origin.get("lon") if origin.get("lon") is not None else focused.get("longitude", -73.99)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)

    if origin.get("lat") is not None and origin.get("lon") is not None:
        folium.Marker(
            [origin["lat"], origin["lon"]],
            popup=f"Current origin · {origin.get('label', 'Current location')}",
            tooltip="Current origin",
            icon=folium.Icon(color="blue", icon="home", prefix="fa"),
        ).add_to(m)

    for item in restaurants:
        lat = item.get("latitude")
        lon = item.get("longitude")
        if not lat or not lon:
            continue

        name = item.get("name", "Restaurant")
        rating = float(item.get("rating", 0.0) or 0.0)
        business_id = item.get("business_id", "")
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
        height=420,
        width=None,
        use_container_width=True,
        returned_objects=["last_object_clicked", "last_object_clicked_tooltip"],
    )

    clicked = _resolve_clicked_business_id(restaurants, payload) if isinstance(payload, dict) else None

    if clicked and clicked != st.session_state.get("focus_business_id"):
        st.session_state.focus_business_id = clicked
        st.session_state.jump_to_business_id = clicked
        st.session_state.page = "Discover"
        st.rerun()
