"""
frontend/components/forgot_password_modal.py
Owner: Jonas Chen

Responsibilities:
- Renders the forgot password modal dialog
- Collects username and replacement password input
- Updates the user's password in MongoDB
- Redirects the user back to the login flow after reset
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import (
    close_forgot_password_modal,
    forgot_password,
    open_login_modal,
)
from frontend.components.dialog_gate import can_open_dialog


def render_forgot_password_modal() -> None:
    if not st.session_state.get("show_forgot_password_modal", False):
        return
    if not can_open_dialog("forgot_password_modal"):
        return

    @st.dialog("Forgot password")
    def _dialog() -> None:
        st.write("Reset your password to regain access to your account.")

        username = st.text_input("Username", key="forgot_modal_username")
        new_password = st.text_input("New password", type="password", key="forgot_modal_new_password")
        confirm_password = st.text_input(
            "Confirm new password",
            type="password",
            key="forgot_modal_confirm_password",
        )

        top_row = st.columns(2)
        with top_row[0]:
            if st.button("Reset password", key="forgot_modal_submit", use_container_width=True):
                success, message = forgot_password(username, new_password, confirm_password)
                if success:
                    st.success(message)
                    st.rerun()
                st.error(message)

        with top_row[1]:
            if st.button("Cancel", key="forgot_modal_cancel", use_container_width=True):
                close_forgot_password_modal()
                st.rerun()

        if st.button("Back to log in", key="forgot_modal_back_to_login", use_container_width=True):
            open_login_modal()
            st.rerun()

    _dialog()