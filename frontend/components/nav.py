"""
frontend/components/nav.py
Owner: Jonas Chen

Responsibilities:
- Renders the top navigation bar
- Displays the NearBite logo and page navigation controls
- Updates page state without leaving the current Streamlit app
- Supports switching between Home, Discover, Profile, and Wrapped
"""

from __future__ import annotations

import streamlit as st

from frontend.theme import asset_to_data_uri

PAGES = ["Home", "Discover", "Profile", "Wrapped"]


def render_nav() -> str:
    current_page = st.session_state.get("page", "Home")
    if current_page not in PAGES:
        current_page = "Home"
        st.session_state.page = "Home"

    logo_uri = asset_to_data_uri("nearbite.svg", "image/svg+xml")

    st.markdown("<div class='nb-topbar-anchor'></div>", unsafe_allow_html=True)

    left, right = st.columns([2.1, 2.7], gap="large", vertical_alignment="center")

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

    with right:
        nav_cols = st.columns(4, gap="small")
        for col, page in zip(nav_cols, PAGES):
            button_type = "primary" if page == current_page else "secondary"
            if col.button(page, key=f"nav_{page}", use_container_width=True, type=button_type):
                st.session_state.page = page
                st.rerun()

    return st.session_state.page