"""
frontend/components/location_picker.py
Owner: Jonas Chen

Responsibilities:
- Renders the current-location control in the Discover page
- Connects browser geolocation to frontend session state
- Keeps the control compact and focused on the location icon
- Displays the best available current-origin label beside the icon
"""

from __future__ import annotations

import textwrap

import streamlit as st
from streamlit_geolocation import streamlit_geolocation

from frontend.adapters import get_current_origin, set_user_origin


def render_location_picker() -> None:
    origin = get_current_origin()

    picker_shell = st.container()
    with picker_shell:
        st.markdown("<div class='nb-panel-title'>Location</div>", unsafe_allow_html=True)
        st.markdown("<div class='nb-location-inline-anchor'></div>", unsafe_allow_html=True)

        left, right = st.columns([0.55, 5.45], gap="small", vertical_alignment="center")

        with left:
            location = streamlit_geolocation()

        with right:
            area_label = origin.get("area_label", "")
            area_html = ""
            if area_label and area_label != origin.get("label"):
                area_html = f"<div class='nb-location-inline-area'>Area: {area_label}</div>"

            st.markdown(
                textwrap.dedent(
                    f"""
                <div class="nb-location-inline">
                  <div class="nb-location-inline-label">Current origin</div>
                  <div class="nb-location-inline-value"><strong>{origin['label']}</strong></div>
                  {area_html}
                </div>
                """
                ).strip(),
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
