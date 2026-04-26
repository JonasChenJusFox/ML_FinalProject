"""
frontend/views/account.py
Owner: Jonas Chen

Responsibilities:
- Renders account entry points without changing auth/session behavior
- Shows logged-in user state
- Keeps login, signup, and logout easy to reach from the main nav
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import logout, open_login_modal, open_signup_modal


def render_account(restaurants: list[dict]) -> None:
    st.markdown("### Account")

    if st.session_state.get("is_logged_in", False):
        current_user = st.session_state.get("current_user", {}) or {}
        display_name = current_user.get("display_name") or current_user.get("username") or "User"
        username = current_user.get("username", "")
        email = current_user.get("email", "")

        st.success(f"Logged in as {display_name}.")
        st.caption(f"Username: {username}")
        if email:
            st.caption(f"Email: {email}")

        cols = st.columns([1, 1, 2], gap="small")
        if cols[0].button("Log out", key="account_logout", use_container_width=True):
            logout()
            st.session_state.page = "Home"
            st.rerun()
        if cols[1].button("Go to Profile", key="account_profile", use_container_width=True):
            st.session_state.page = "Profile"
            st.rerun()
        return

    st.info("Log in or create an account to save restaurants, like places, write reviews, and personalize recommendations.")
    cols = st.columns(2, gap="small")
    if cols[0].button("Log in", key="account_login", use_container_width=True):
        open_login_modal()
        st.rerun()
    if cols[1].button("Sign up", key="account_signup", use_container_width=True):
        open_signup_modal()
        st.rerun()
