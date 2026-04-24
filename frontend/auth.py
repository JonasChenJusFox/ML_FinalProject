"""
frontend/auth.py
Owner: Jonas Chen

Responsibilities:
- Manages authentication state for the Streamlit app
- Stores login, logout, and modal visibility logic
- Connects sign up, login, and password reset flows to MongoDB
- Keeps current user identity in Streamlit session state
- Synchronizes saved restaurant ids after login and logout
"""

from __future__ import annotations

import streamlit as st

from integration.db import (
    create_user,
    find_user_by_credentials,
    find_user_by_username,
    get_liked_restaurant_ids,
    get_saved_restaurant_ids,
    has_secret_question,
    is_valid_secret_question,
    reset_user_password,
    set_secret_question,
    verify_secret_question_answer,
)


def _clear_widget_trigger_state(*keys: str) -> None:
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def _clear_account_security_widget_state() -> None:
    _clear_widget_trigger_state(
        "nav_menu_button",
        "account_security_modal_close",
        "nav_popover_login",
        "nav_popover_signup",
        "nav_popover_logout",
    )


def init_auth_state() -> None:
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False

    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    if "show_login_modal" not in st.session_state:
        st.session_state.show_login_modal = False

    if "show_signup_modal" not in st.session_state:
        st.session_state.show_signup_modal = False

    if "show_forgot_password_modal" not in st.session_state:
        st.session_state.show_forgot_password_modal = False

    if "show_account_security_modal" not in st.session_state:
        st.session_state.show_account_security_modal = False

    if "show_questionnaire_modal" not in st.session_state:
        st.session_state.show_questionnaire_modal = False

    if "saved_ids" not in st.session_state:
        st.session_state.saved_ids = []

    if "liked_ids" not in st.session_state:
        st.session_state.liked_ids = []


def _complete_login(user: dict) -> None:
    st.session_state.is_logged_in = True
    st.session_state.current_user = {
        "username": user["username"],
        "display_name": user.get("display_name", user["username"]),
        "email": user.get("email", ""),
    }
    st.session_state.saved_ids = get_saved_restaurant_ids(user["username"])
    st.session_state.liked_ids = get_liked_restaurant_ids(user["username"])
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()


def open_login_modal() -> None:
    st.session_state.show_login_modal = True
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()


def close_login_modal() -> None:
    st.session_state.show_login_modal = False


def open_signup_modal() -> None:
    st.session_state.show_signup_modal = True
    st.session_state.show_login_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()


def close_signup_modal() -> None:
    st.session_state.show_signup_modal = False


def open_forgot_password_modal() -> None:
    st.session_state.show_forgot_password_modal = True
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()


def close_forgot_password_modal() -> None:
    st.session_state.show_forgot_password_modal = False


def open_account_security_modal() -> None:
    st.session_state.show_account_security_modal = True
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()


def close_account_security_modal() -> None:
    st.session_state.show_account_security_modal = False
    _clear_account_security_widget_state()


def open_questionnaire_modal() -> None:
    st.session_state.show_questionnaire_modal = True
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()


def close_questionnaire_modal() -> None:
    st.session_state.show_questionnaire_modal = False


def login(username: str, password: str) -> tuple[bool, str]:
    normalized = username.strip().lower()
    if not normalized:
        return False, "Username is required."

    if not password:
        return False, "Password is required."

    user = find_user_by_credentials(normalized, password, identity_type="username")
    if not user:
        return False, "Invalid username or password."

    _complete_login(user)
    return True, "Logged in successfully."


def signup(
    username: str,
    password: str,
    confirm_password: str,
    secret_question_prompt: str,
    secret_answer: str,
) -> tuple[bool, str]:
    normalized = username.strip().lower()
    display_name = username.strip()

    if not normalized:
        return False, "Username is required."

    if not password:
        return False, "Password is required."

    if password != confirm_password:
        return False, "Passwords do not match."

    if not is_valid_secret_question(secret_question_prompt):
        return False, "Please choose one of the provided secret questions."

    if not str(secret_answer or "").strip():
        return False, "Secret answer is required."

    existing = find_user_by_username(normalized)
    if existing:
        return False, "That username already exists."

    create_user(
        username=normalized,
        password=password,
        display_name=display_name,
        secret_question_prompt=secret_question_prompt,
        secret_answer=secret_answer,
    )

    user = find_user_by_username(normalized)
    if not user:
        return False, "We could not create your account. Please try again."

    st.session_state.saved_ids = []
    st.session_state.liked_ids = []
    _complete_login(user)
    return True, "Account created successfully."


def forgot_password(
    username: str,
    secret_answer: str,
    new_password: str,
    confirm_password: str,
) -> tuple[bool, str]:
    normalized = username.strip().lower()

    if not normalized:
        return False, "Username is required."

    if not new_password:
        return False, "New password is required."

    if new_password != confirm_password:
        return False, "Passwords do not match."

    user = find_user_by_username(normalized)
    if not user:
        return False, "No account found with that username."

    if not has_secret_question(normalized):
        return False, "This account does not have a secret question on file yet."

    if not verify_secret_question_answer(normalized, secret_answer):
        return False, "The secret answer does not match our records."

    reset_user_password(normalized, new_password)
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_login_modal = True
    return True, "Password updated successfully. Please log in."


def reset_password_with_secret_question(
    username: str,
    secret_answer: str,
    new_password: str,
    confirm_password: str,
) -> tuple[bool, str]:
    normalized = str(username or "").strip().lower()

    if not normalized:
        return False, "Username is required."

    if not has_secret_question(normalized):
        return False, "Set up a secret question before resetting your password."

    if not str(secret_answer or "").strip():
        return False, "Secret answer is required."

    if not new_password:
        return False, "New password is required."

    if new_password != confirm_password:
        return False, "Passwords do not match."

    if not verify_secret_question_answer(normalized, secret_answer):
        return False, "The secret answer does not match our records."

    reset_user_password(normalized, new_password)
    return True, "Password updated successfully."


def save_secret_question_for_user(
    username: str,
    secret_question_prompt: str,
    secret_answer: str,
) -> tuple[bool, str]:
    normalized = str(username or "").strip().lower()

    if not normalized:
        return False, "Username is required."

    if not is_valid_secret_question(secret_question_prompt):
        return False, "Please choose one of the provided secret questions."

    if not str(secret_answer or "").strip():
        return False, "Secret answer is required."

    if has_secret_question(normalized):
        return False, "This account already has a secret question on file."

    set_secret_question(normalized, secret_question_prompt, secret_answer)
    return True, "Secret question saved successfully."


def logout() -> None:
    st.session_state.is_logged_in = False
    st.session_state.current_user = None
    st.session_state.saved_ids = []
    st.session_state.liked_ids = []
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_account_security_widget_state()
    _clear_account_security_widget_state()
