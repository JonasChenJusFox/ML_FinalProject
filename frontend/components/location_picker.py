"""
frontend/components/location_picker.py
Owner: Jonas Chen

Responsibilities:
- Renders the current-location control in the Discover page
- Connects browser geolocation to frontend session state
- Allows the app to switch from the default NYU origin to the user's location
- Supports location-based travel-time filtering
"""

from __future__ import annotations

import streamlit as st
from streamlit_geolocation import streamlit_geolocation

from frontend.adapters import get_current_origin, set_user_origin


def render_location_picker() -> None:
    origin = get_current_origin()

    st.markdown("<div class='nb-panel-title'>Location</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='nb-location-bar-anchor'></div>", unsafe_allow_html=True)
        left, right = st.columns([0.9, 4.1], gap="small", vertical_alignment="center")

        with left:
            location = streamlit_geolocation()

        with right:
            st.markdown(
                f"""
                <div class="nb-location-bar-copy">
                  <div class="nb-location-bar-title">Use current location</div>
                  <div class="nb-location-bar-subtitle">Current origin: {origin['label']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if isinstance(location, dict):
        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat is not None and lon is not None:
            lat = float(lat)
            lon = float(lon)

            prev_lat = st.session_state.get("user_lat")
            prev_lon = st.session_state.get("user_lon")
            using_my_location = st.session_state.get("use_my_location", False)

            if prev_lat != lat or prev_lon != lon or not using_my_location:
                set_user_origin(lat, lon)
                st.toast("Using your current location.")
                st.rerun()