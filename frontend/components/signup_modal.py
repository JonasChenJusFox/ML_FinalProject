"""Signup ``@st.dialog``: new user fields, MongoDB create, and immediate login."""

from __future__ import annotations

import streamlit as st

from frontend.auth import close_signup_modal, open_login_modal, signup
from frontend.components.dialog_gate import can_open_dialog


def render_signup_modal() -> None:
    if not st.session_state.get("show_signup_modal", False):
        return
    if not can_open_dialog("signup_modal"):
        return

    @st.dialog("Sign up", on_dismiss=close_signup_modal)
    def _dialog() -> None:
        st.write("Create an account to save restaurants and receive personalized recommendations.")

        username = st.text_input("Username", key="signup_modal_username")
        email = st.text_input("Email", key="signup_modal_email")
        password = st.text_input("Password", type="password", key="signup_modal_password")
        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            key="signup_modal_confirm_password",
        )

        top_row = st.columns(2)
        with top_row[0]:
            if st.button("Create account", key="signup_modal_submit", use_container_width=True):
                success, message = signup(username, email, password, confirm_password)
                if success:
                    st.success(message)
                    st.rerun()
                st.error(message)

        with top_row[1]:
            if st.button("Cancel", key="signup_modal_cancel", use_container_width=True):
                close_signup_modal()
                st.rerun()

        if st.button("Already have an account? Log in", key="signup_modal_back_to_login", use_container_width=True):
            open_login_modal()
            st.rerun()

    _dialog()