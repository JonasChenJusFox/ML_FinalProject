"""
frontend/components/questionnaire_modal.py

Global dialog wrapper for the questionnaire flow.
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import close_questionnaire_modal
from frontend.components.onboarding_form import render_onboarding_form


def render_questionnaire_modal() -> None:
    if not st.session_state.get("show_questionnaire_modal", False):
        return

    if not st.session_state.get("is_logged_in", False):
        close_questionnaire_modal()
        return

    if any(
        [
            st.session_state.get("show_login_modal", False),
            st.session_state.get("show_signup_modal", False),
            st.session_state.get("show_forgot_password_modal", False),
            st.session_state.get("show_account_security_modal", False),
            st.session_state.get("show_comments_modal", False),
        ]
    ):
        close_questionnaire_modal()
        return

    @st.dialog("Questionnaire")
    def _dialog() -> None:
        st.caption("Help us to make better recommendations for you.")
        render_onboarding_form(show_header=False)

        if st.button("Close", key="questionnaire_modal_close", use_container_width=True):
            close_questionnaire_modal()
            st.rerun()

    _dialog()
