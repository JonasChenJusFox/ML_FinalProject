"""
frontend/components/signup_modal.py
Owner: Jonas Chen

Responsibilities:
- Renders the sign up modal dialog
- Collects username and password input
- Creates a new user account in MongoDB
- Logs the user in immediately after successful account creation
"""

from __future__ import annotations

import streamlit as st

from frontend.auth import close_signup_modal, open_login_modal, signup
from integration.db import get_secret_questions


@st.dialog("Sign up")
def _render_signup_dialog() -> None:
    st.write(
        "Create an account to save restaurants and receive personalized recommendations."
    )

    username = st.text_input("Username", key="signup_modal_username")
    password = st.text_input("Password", type="password", key="signup_modal_password")
    confirm_password = st.text_input(
        "Confirm password",
        type="password",
        key="signup_modal_confirm_password",
    )
    st.markdown("<div class='nb-secret-question-anchor'></div>", unsafe_allow_html=True)
    secret_question_prompt = st.selectbox(
        "Secret question",
        options=get_secret_questions(),
        key="signup_modal_secret_question",
    )
    secret_answer = st.text_input(
        "Secret answer",
        type="password",
        key="signup_modal_secret_answer",
    )

    top_row = st.columns(2)
    with top_row[0]:
        if st.button("Create account", key="signup_modal_submit", use_container_width=True):
            success, message = signup(
                username,
                password,
                confirm_password,
                secret_question_prompt,
                secret_answer,
            )
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


def render_signup_modal() -> None:
    if not st.session_state.get("show_signup_modal", False):
        return

    _render_signup_dialog()
