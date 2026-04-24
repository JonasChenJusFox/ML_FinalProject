"""
frontend/components/account_security_modal.py
Owner: Jonas Chen

Responsibilities:
- Opens the global account dialog from the top-right menu
- Prevents account modal conflicts with login, signup, forgot-password, and comments dialogs
- Resets the one-shot account modal flag after rendering
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import close_account_security_modal
from frontend.components.account_security_menu import render_account_security_menu


def render_account_security_modal() -> None:
    if not st.session_state.get("show_account_security_modal", False):
        return

    if any(
        [
            st.session_state.get("show_login_modal", False),
            st.session_state.get("show_signup_modal", False),
            st.session_state.get("show_forgot_password_modal", False),
            st.session_state.get("show_comments_modal", False),
        ]
    ):
        close_account_security_modal()
        return

    @st.dialog("Account")
    def _dialog() -> None:
        render_account_security_menu()

        if st.button("Close", key="account_security_modal_close", use_container_width=True):
            close_account_security_modal()
            st.rerun()

    _dialog()
    st.session_state.show_account_security_modal = False
