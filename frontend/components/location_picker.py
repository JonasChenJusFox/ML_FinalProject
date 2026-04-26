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

from embeddings.location_lookup import lookup_zipcode_coordinate
from frontend.adapters import get_current_origin, reset_origin_to_nyu, set_user_origin


def render_location_picker() -> None:
    origin = get_current_origin()

    st.markdown("<div class='nb-panel-title'>Location</div>", unsafe_allow_html=True)
    st.caption(f"Selected origin: {origin['label']} ({origin['lat']:.4f}, {origin['lon']:.4f})")

    mode_options = ["NYU / campus", "Current location", "Zip code"]
    current_label = origin.get("label", "NYU")
    default_index = 0
    if current_label.startswith("ZIP"):
        default_index = 2
    elif st.session_state.get("use_my_location", False):
        default_index = 1

    mode = st.radio(
        "Choose search origin",
        options=mode_options,
        index=default_index,
        horizontal=True,
        key="discover_location_mode",
    )

    if mode == "NYU / campus":
        if st.session_state.get("use_my_location", False):
            reset_origin_to_nyu()
            st.toast("Using NYU as your search origin.")
            st.rerun()
        return

    if mode == "Zip code":
        cols = st.columns([3, 1], gap="small")
        with cols[0]:
            zipcode = st.text_input(
                "Zip code",
                key="discover_zipcode",
                placeholder="10003",
            )
        with cols[1]:
            apply_zip = st.button("Use zip", key="discover_use_zip", use_container_width=True)

        if apply_zip:
            coords = lookup_zipcode_coordinate(zipcode.strip())
            if coords:
                lat, lon = coords
                set_user_origin(lat, lon, label=f"ZIP {zipcode.strip()}")
                st.toast(f"Using ZIP {zipcode.strip()} as your search origin.")
                st.rerun()
            else:
                st.warning("That NYC zip code was not found in the local location data.")
        return

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
                set_user_origin(lat, lon, label="Current location")
                st.toast("Using your current location.")
                st.rerun()
