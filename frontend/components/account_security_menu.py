"""
frontend/components/account_security_menu.py

Renders the account and security controls inside the top-right menu.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from frontend.auth import (
    close_account_security_modal,
    logout,
    open_login_modal,
    open_signup_modal,
    reset_password_with_secret_question,
    save_secret_question_for_user,
)
from integration.account_service import clear_personalization_data, delete_account
from integration.user_repo import (
    find_user_by_username,
    get_secret_questions,
    has_secret_question,
    set_personalization_state,
    verify_secret_question_answer,
)
from integration.wrapped_repo import build_wrapped_stats


def _format_datetime(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%b %d, %Y")
        except ValueError:
            return value
    return "Unknown"


def _render_account_summary(user: dict) -> None:
    username = str(user.get("display_name", user.get("username", "")) or "")
    created_at = _format_datetime(user.get("created_at"))

    st.markdown("##### Account info")
    st.caption(f"Username: {username}")
    st.caption(f"Member since: {created_at}")
    st.caption("Password: Hidden. Secret question verification is required before any password reset.")


def _render_secret_question_setup(username: str, user: dict) -> None:
    if user.get("secret_question_prompt"):
        return

    st.markdown("##### Secret question")
    st.warning(
        "This older account does not have a secret question yet. "
        "Set one now to unlock password recovery and account protection."
    )

    with st.form("account_secret_question_form"):
        st.markdown("<div class='nb-secret-question-anchor'></div>", unsafe_allow_html=True)
        secret_question_prompt = st.selectbox(
            "Choose a secret question",
            options=get_secret_questions(),
            key="account_secret_question_prompt",
        )
        secret_answer = st.text_input(
            "Secret answer",
            type="password",
            key="account_secret_question_answer",
        )
        submitted = st.form_submit_button("Save secret question", use_container_width=True)

    if submitted:
        success, message = save_secret_question_for_user(
            username,
            secret_question_prompt,
            secret_answer,
        )
        if success:
            st.toast(message)
            st.rerun()
        st.error(message)


def _render_reset_password(username: str, user: dict) -> None:
    st.markdown("##### Reset password")
    secret_question_prompt = str(user.get("secret_question_prompt", "") or "")

    if not secret_question_prompt:
        st.info("Set a secret question first. Password reset is locked until the question is saved.")
        return

    st.caption(f"Verification question: {secret_question_prompt}")
    with st.form("account_reset_password_form"):
        secret_answer = st.text_input(
            "Secret answer",
            type="password",
            key="account_reset_secret_answer",
        )
        new_password = st.text_input(
            "New password",
            type="password",
            key="account_reset_new_password",
        )
        confirm_password = st.text_input(
            "Confirm new password",
            type="password",
            key="account_reset_confirm_password",
        )
        submitted = st.form_submit_button("Update password", use_container_width=True)

    if submitted:
        success, message = reset_password_with_secret_question(
            username,
            secret_answer,
            new_password,
            confirm_password,
        )
        if success:
            close_account_security_modal()
            st.toast(message)
            st.rerun()
        st.error(message)


def _render_delete_account(username: str, user: dict) -> None:
    st.markdown("##### Delete account")
    st.caption("This permanently removes your account, saved restaurants, reviews, and profile data.")

    if not has_secret_question(username):
        st.info("Set a secret question before you can delete this account.")
        return

    with st.form("account_delete_form"):
        confirm_username = st.text_input(
            "Type your username to confirm",
            key="account_delete_confirm_username",
        )
        secret_answer = st.text_input(
            "Secret answer",
            type="password",
            key="account_delete_secret_answer",
        )
        submitted = st.form_submit_button("Delete account", use_container_width=True)

    if submitted:
        if confirm_username.strip().lower() != username:
            st.error("The confirmation username does not match this account.")
            return

        if not verify_secret_question_answer(username, secret_answer):
            st.error("The secret answer does not match our records.")
            return

        delete_account(username)
        close_account_security_modal()
        logout()
        st.session_state.page = "Home"
        st.toast("Your account has been deleted.")
        st.rerun()


def _render_account_tab() -> None:
    current_user = st.session_state.get("current_user", {}) or {}
    username = str(current_user.get("username", "") or "").strip().lower()
    if not username:
        st.info("Log in to manage your account.")
        return

    user = find_user_by_username(username) or {}
    _render_account_summary(user)
    if not user.get("secret_question_prompt"):
        st.divider()
        _render_secret_question_setup(username, user)
    st.divider()
    _render_reset_password(username, user)
    st.divider()
    _render_delete_account(username, user)


def _render_security_tab() -> None:
    current_user = st.session_state.get("current_user", {}) or {}
    username = str(current_user.get("username", "") or "").strip().lower()
    if not username:
        st.info("Log in to manage security settings.")
        return

    user = find_user_by_username(username) or {}
    personalization_enabled = bool(user.get("personalization_enabled", True))
    status_label = "On" if personalization_enabled else "Paused"

    st.markdown("##### Personalization")
    st.caption(f"Status: {status_label}")

    if personalization_enabled:
        if st.button("Pause personalization", key="security_pause_personalization", use_container_width=True):
            preview_restaurants = st.session_state.get("preview_restaurants", []) or []
            frozen_stats = build_wrapped_stats(username, preview_restaurants)
            set_personalization_state(
                username,
                False,
                frozen_personalization=frozen_stats,
            )
            st.toast("Personalization paused. We will keep your current preferences without learning from new activity.")
            st.rerun()
    else:
        if st.button("Resume personalization", key="security_resume_personalization", use_container_width=True):
            set_personalization_state(
                username,
                True,
                frozen_personalization=None,
            )
            st.toast("Personalization resumed.")
            st.rerun()

    st.divider()
    st.markdown("##### Delete personalization data")
    st.caption(
        "This clears questionnaire-based and behavior-based personalization data. "
        "Your public reviews stay visible, but they will stop affecting recommendations."
    )

    confirm_clear = st.text_input(
        "Type CLEAR to confirm",
        key="security_clear_personalization_confirm",
    )
    if st.button("Delete personalization data", key="security_clear_personalization", use_container_width=True):
        if confirm_clear.strip().upper() != "CLEAR":
            st.error("Type CLEAR before deleting personalization data.")
            return

        clear_personalization_data(username)
        close_account_security_modal()
        st.session_state.saved_ids = []
        st.toast("Personalization data deleted.")
        st.rerun()


def render_account_security_menu() -> None:
    if st.session_state.get("is_logged_in", False):
        current_user = st.session_state.get("current_user", {}) or {}
        display_name = current_user.get("display_name", "User")
        st.caption(f"Logged in as {display_name}")

        account_tab, security_tab = st.tabs(["Account", "Security"])
        with account_tab:
            _render_account_tab()
        with security_tab:
            _render_security_tab()

        if st.button("Log out", key="nav_popover_logout", use_container_width=True):
            close_account_security_modal()
            logout()
            st.session_state.page = "Home"
            st.rerun()
        return

    st.write("Log in to manage your account and privacy settings.")
    row = st.columns(2, gap="small")
    if row[0].button("Log in", key="nav_popover_login", use_container_width=True):
        close_account_security_modal()
        open_login_modal()
        st.rerun()
    if row[1].button("Sign up", key="nav_popover_signup", use_container_width=True):
        close_account_security_modal()
        open_signup_modal()
        st.rerun()
