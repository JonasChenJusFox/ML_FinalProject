"""
frontend/components/post_signup_questionnaire_dialog.py

Responsibilities:
- Opens the onboarding questionnaire in a dialog immediately after sign-up
- Avoids duplicate form widgets by coordinating with the Profile page gate
"""

from __future__ import annotations

import streamlit as st

from frontend.components.onboarding_form import render_onboarding_form
from frontend.components.dialog_gate import can_open_dialog


def render_post_signup_questionnaire_dialog() -> None:
    if not st.session_state.get("show_post_signup_questionnaire", False):
        return
    if not st.session_state.get("is_logged_in", False):
        st.session_state.show_post_signup_questionnaire = False
        return
    if st.session_state.get("onboarding_completed", False):
        st.session_state.show_post_signup_questionnaire = False
        return
    if not can_open_dialog("post_signup_questionnaire"):
        return

    @st.dialog("Complete your taste profile")
    def _dialog() -> None:
        st.caption("Tell us a bit about your taste so Home and Discover can personalize results.")
        render_onboarding_form()
        if st.button("Not now", key="post_signup_questionnaire_skip", use_container_width=True):
            st.session_state.show_post_signup_questionnaire = False
            st.rerun()

    _dialog()
