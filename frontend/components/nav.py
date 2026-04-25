"""
frontend/components/nav.py
Owner: Jonas Chen

Responsibilities:
- Renders the standard top navigation bar for the NearBite app
- Displays the NearBite logo and main navigation controls
- Supports switching between Home, Discover, and Profile
- Provides login and logout actions inside a utility hamburger menu
- Uses a normal top layout without sticky or fixed behavior
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import logout, open_login_modal, open_signup_modal
from frontend.theme import asset_to_data_uri

PAGES = ["Home", "Discover", "Profile"]


def _init_nav_state() -> None:
    if "show_nav_menu" not in st.session_state:
        st.session_state.show_nav_menu = False


def render_nav() -> str:
    _init_nav_state()

    current_page = st.session_state.get("page", "Home")
    if current_page not in PAGES:
        current_page = "Home"
        st.session_state.page = "Home"

    logo_uri = asset_to_data_uri("nearbite.svg", "image/svg+xml")

    st.markdown("<div class='nb-topbar-standard'>", unsafe_allow_html=True)

    left, middle, right = st.columns([2.0, 5.2, 0.9], gap="small", vertical_alignment="center")

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
                st.session_state.show_nav_menu = False
                st.rerun()

    with right:
        if st.button("☰", key="nav_hamburger", use_container_width=True):
            st.session_state.show_nav_menu = not st.session_state.show_nav_menu
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("show_nav_menu", False):
        st.markdown("<div class='nb-nav-menu-panel'>", unsafe_allow_html=True)

        if st.session_state.get("is_logged_in", False):
            current_user = st.session_state.get("current_user", {})
            st.markdown(
                f"""
                <div class="nb-nav-user-label">
                  Logged in as <strong>{current_user.get("display_name", "User")}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Log out", key="menu_logout", use_container_width=True):
                logout()
                st.session_state.page = "Home"
                st.session_state.show_nav_menu = False
                st.rerun()
        else:
            st.markdown(
                """
                <div class="nb-nav-user-label">
                  You are not logged in
                </div>
                """,
                unsafe_allow_html=True,
            )

            auth_cols = st.columns(2, gap="small")
            if auth_cols[0].button("Log in", key="menu_login", use_container_width=True):
                open_login_modal()
                st.session_state.show_nav_menu = False
                st.rerun()
            if auth_cols[1].button("Sign up", key="menu_signup", use_container_width=True):
                open_signup_modal()
                st.session_state.show_nav_menu = False
                st.rerun()

        if st.button("Close", key="menu_close", use_container_width=True):
            st.session_state.show_nav_menu = False
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state.page
