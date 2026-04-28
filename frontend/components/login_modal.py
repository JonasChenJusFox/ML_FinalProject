"""
frontend/components/login_modal.py
Owner: Jonas Chen

Responsibilities:
- Renders the login modal dialog
- Collects username and password input
- Supports navigation to sign up and forgot password flows
- Updates authentication state after successful login
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import (
    close_login_modal,
    login,
    open_forgot_password_modal,
    open_signup_modal,
)
from frontend.components.dialog_gate import can_open_dialog


def render_login_modal() -> None:
    if not st.session_state.get("show_login_modal", False):
        return
    if not can_open_dialog("login_modal"):
        return

    @st.dialog("Log in")
    def _dialog() -> None:
        st.write("Log in to save restaurants, view your profile, and get personalized recommendations.")

        username = st.text_input("Username", key="login_modal_username")
        password = st.text_input("Password", type="password", key="login_modal_password")

        top_row = st.columns(2)
        with top_row[0]:
            if st.button("Log in", key="login_modal_submit", use_container_width=True):
                success, message = login(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                st.error(message)

        with top_row[1]:
            if st.button("Cancel", key="login_modal_cancel", use_container_width=True):
                close_login_modal()
                st.rerun()

        bottom_row = st.columns(2)
        with bottom_row[0]:
            if st.button("Sign up", key="login_modal_signup", use_container_width=True):
                open_signup_modal()
                st.rerun()

        with bottom_row[1]:
            if st.button("Forgot password", key="login_modal_forgot", use_container_width=True):
                open_forgot_password_modal()
                st.rerun()

    _dialog()