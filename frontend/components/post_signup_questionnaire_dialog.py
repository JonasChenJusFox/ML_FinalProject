"""Post-signup questionnaire dialog; coordinates with profile page to avoid duplicate widgets."""

from __future__ import annotations

import streamlit as st

from frontend.components.onboarding_form import render_onboarding_form
from frontend.components.dialog_gate import can_open_dialog


def _dismiss_post_signup_questionnaire_dialog() -> None:
    st.session_state.show_post_signup_questionnaire = False


def render_post_signup_questionnaire_dialog() -> None:
    if not st.session_state.get("show_post_signup_questionnaire", False):
        return
    if not st.session_state.get("is_logged_in", False):
        st.session_state.show_post_signup_questionnaire = False
        return
    if not can_open_dialog("post_signup_questionnaire"):
        return

    @st.dialog(
        "Complete your taste profile",
        on_dismiss=_dismiss_post_signup_questionnaire_dialog,
    )
    def _dialog() -> None:
        if not st.session_state.get("onboarding_completed", False):
            st.caption("Tell us a bit about your taste so Home and Discover can personalize results.")
        else:
            st.caption("Update your preferences anytime to improve recommendations.")
        render_onboarding_form()
        if st.button("Not now", key="post_signup_questionnaire_skip", use_container_width=True):
            st.session_state.show_post_signup_questionnaire = False
            st.rerun()

    _dialog()
