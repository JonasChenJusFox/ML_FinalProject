"""Folium map of results with marker clicks driving focus and the restaurant profile dialog."""

from __future__ import annotations

import math

import folium
import streamlit as st
from streamlit_folium import st_folium

USER_LOCATION_POPUP = "Your location (search origin)"


def clear_discover_map_pin_selection() -> None:
    """
    Clear focused pin, profile dialog target, and click dedupe state.
    Bumps the Folium widget key so streamlit-folium remounts and drops stale last_object_clicked data.
    """
    st.session_state.focus_business_id = None
    st.session_state.restaurant_profile_business_id = None
    st.session_state._map_click_intent_handled = None
    if "jump_to_business_id" in st.session_state:
        del st.session_state["jump_to_business_id"]
    st.session_state.discover_folium_map_layout_key = int(
        st.session_state.get("discover_folium_map_layout_key", 0)
    ) + 1


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers (Earth mean radius)."""
    radius_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(a)))


def _nearest_business_id(
    restaurants: list[dict],
    lat: float,
    lon: float,
    max_km: float = 0.1,
) -> str | None:
    """Return business_id of the nearest restaurant pin within max_km, or None."""
    best_id: str | None = None
    best_d = max_km
    for item in restaurants:
        try:
            rlat = float(item.get("latitude"))
            rlon = float(item.get("longitude"))
        except (TypeError, ValueError):
            continue
        d = _haversine_km(lat, lon, rlat, rlon)
        if d < best_d:
            best_d = d
            bid = item.get("business_id")
            if bid:
                best_id = str(bid)
    return best_id


def _map_click_intent_key(
    clicked_business_id: str,
    clicked_latlon: tuple[float, float] | None,
    clicked_popup: str | None,
) -> str:
    if clicked_latlon:
        lat, lon = clicked_latlon
        return f"ll:{lat:.6f},{lon:.6f}:{clicked_business_id}"
    return f"pop:{clicked_popup or ''}:{clicked_business_id}"


def render_map(restaurants: list[dict]) -> None:
    if not restaurants:
        st.info("No restaurants to map.")
        return

    focus_id = st.session_state.get("focus_business_id")
    focused = next(
        (r for r in restaurants if str(r.get("business_id", "")) == str(focus_id)),
        restaurants[0],
    )

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
        is_focus = focus_id is not None and str(business_id) == str(focus_id)

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

    # User-chosen "Current location" (Discover geolocation) — draw on top of restaurant pins.
    if (
        st.session_state.get("use_my_location", False)
        and st.session_state.get("user_lat") is not None
        and st.session_state.get("user_lon") is not None
    ):
        try:
            user_lat = float(st.session_state["user_lat"])
            user_lon = float(st.session_state["user_lon"])
        except (TypeError, ValueError):
            user_lat = user_lon = None
        if user_lat is not None and user_lon is not None:
            folium.CircleMarker(
                location=[user_lat, user_lon],
                radius=10,
                color="#1e40af",
                weight=2,
                fill=True,
                fill_color="#3b82f6",
                fill_opacity=0.9,
                popup=USER_LOCATION_POPUP,
                tooltip="Your location",
            ).add_to(m)

    folium_key = int(st.session_state.get("discover_folium_map_layout_key", 0))
    payload = st_folium(
        m,
        width=None,
        height=420,
        returned_objects=["last_object_clicked_popup", "last_object_clicked"],
        key=f"discover_folium_{folium_key}",
    )

    clicked_popup: str | None = None
    clicked_latlon: tuple[float, float] | None = None
    if isinstance(payload, dict):
        lp = payload.get("last_object_clicked_popup")
        if isinstance(lp, str) and lp.strip():
            clicked_popup = lp.strip()
        lc = payload.get("last_object_clicked")
        if isinstance(lc, dict) and lc.get("lat") is not None and lc.get("lng") is not None:
            try:
                clicked_latlon = (float(lc["lat"]), float(lc["lng"]))
            except (TypeError, ValueError):
                clicked_latlon = None

    is_user_location = bool(clicked_popup and USER_LOCATION_POPUP in clicked_popup)

    clicked_business_id: str | None = None
    if not is_user_location and clicked_latlon:
        lat, lon = clicked_latlon
        clicked_business_id = _nearest_business_id(restaurants, lat, lon)

    if not clicked_business_id and clicked_popup and not is_user_location and "· ⭐" in clicked_popup:
        name = clicked_popup.split(" · ⭐ ", 1)[0].strip()
        clicked_restaurant = next((item for item in restaurants if item.get("name") == name), None)
        if clicked_restaurant and clicked_restaurant.get("business_id"):
            clicked_business_id = str(clicked_restaurant.get("business_id"))

    if not clicked_business_id:
        return

    intent_key = _map_click_intent_key(clicked_business_id, clicked_latlon, clicked_popup)
    if intent_key == st.session_state.get("_map_click_intent_handled"):
        return

    st.session_state._map_click_intent_handled = intent_key
    st.session_state.focus_business_id = clicked_business_id
    st.session_state.jump_to_business_id = clicked_business_id
    st.session_state.restaurant_profile_business_id = clicked_business_id
    st.session_state.page = "Discover"
    # Do not call st.rerun() here: it can abort the rest of Discover before the profile dialog runs,
    # and streamlit-folium already triggers a rerun when the map returns new interaction data.
