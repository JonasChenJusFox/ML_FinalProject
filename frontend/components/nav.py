"""
frontend/components/nav.py
Owner: Jonas Chen

Responsibilities:
- Renders the standard top navigation bar for the NearBite app
- Displays the NearBite logo and main navigation controls
- Supports switching between Home, Discover, Profile, and Account
- Uses a normal top layout without sticky or fixed behavior
"""

from __future__ import annotations

import streamlit as st

from frontend.components.map_view import clear_discover_map_pin_selection
from frontend.theme import asset_to_data_uri

PAGES = ["Home", "Discover", "Profile", "Account"]


def render_nav() -> str:
    current_page = st.session_state.get("page", "Home")
    if current_page not in PAGES:
        current_page = "Home"
        st.session_state.page = "Home"

    logo_uri = asset_to_data_uri("nearbite.svg", "image/svg+xml")

    st.markdown("<div class='nb-topbar-standard'>", unsafe_allow_html=True)

    left, middle = st.columns([2.0, 5.6], gap="small", vertical_alignment="center")

    with left:
        st.markdown(
            f"""
            <div class="nb-logo-lockup">
              <img src="{logo_uri}" alt="NearBite logo" class="nb-logo-img" />
              <div class="nb-logo-text">
                <div class="nb-brand-name">NearBite</div>
                <div class="nb-brand-subtitle">NYC restaurant discovery</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with middle:
        nav_cols = st.columns(len(PAGES), gap="small")
        for col, page in zip(nav_cols, PAGES):
            button_type = "primary" if page == current_page else "secondary"
            if col.button(
                page,
                key=f"topnav_{page}",
                use_container_width=True,
                type=button_type,
            ):
                st.session_state.page = page
                if page != "Discover":
                    clear_discover_map_pin_selection()
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state.page
