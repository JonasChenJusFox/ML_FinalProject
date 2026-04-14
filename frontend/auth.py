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

from integration.interaction_repo import get_saved_restaurant_ids
from integration.user_repo import (
    create_user,
    find_user_by_credentials,
    find_user_by_username,
    reset_user_password,
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

    if "saved_ids" not in st.session_state:
        st.session_state.saved_ids = []


def open_login_modal() -> None:
    st.session_state.show_login_modal = True
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False


def close_login_modal() -> None:
    st.session_state.show_login_modal = False


def open_signup_modal() -> None:
    st.session_state.show_signup_modal = True
    st.session_state.show_login_modal = False
    st.session_state.show_forgot_password_modal = False


def close_signup_modal() -> None:
    st.session_state.show_signup_modal = False


def open_forgot_password_modal() -> None:
    st.session_state.show_forgot_password_modal = True
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False


def close_forgot_password_modal() -> None:
    st.session_state.show_forgot_password_modal = False


def login(username: str, password: str) -> tuple[bool, str]:
    normalized = username.strip().lower()
    user = find_user_by_credentials(normalized, password)

    if not user:
        return False, "Invalid username or password."

    st.session_state.is_logged_in = True
    st.session_state.current_user = {
        "username": user["username"],
        "display_name": user.get("display_name", user["username"]),
        "email": user.get("email", ""),
    }
    st.session_state.show_login_modal = False
    st.session_state.saved_ids = get_saved_restaurant_ids(user["username"])
    return True, "Logged in successfully."


def signup(username: str, email: str, password: str, confirm_password: str) -> tuple[bool, str]:
    normalized = username.strip().lower()
    email_clean = email.strip().lower()

    if not normalized:
        return False, "Username is required."

    if not email_clean:
        return False, "Email is required."

    if not password:
        return False, "Password is required."

    if password != confirm_password:
        return False, "Passwords do not match."

    existing = find_user_by_username(normalized)
    if existing:
        return False, "That username already exists."

    create_user(
        username=normalized,
        email=email_clean,
        password=password,
        display_name=username.strip(),
    )

    st.session_state.is_logged_in = True
    st.session_state.current_user = {
        "username": normalized,
        "display_name": username.strip(),
        "email": email_clean,
    }
    st.session_state.saved_ids = []
    st.session_state.show_signup_modal = False
    return True, "Account created successfully."


def forgot_password(username: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
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

    reset_user_password(normalized, new_password)
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_login_modal = True
    return True, "Password reset successfully. Please log in."


def logout() -> None:
    st.session_state.is_logged_in = False
    st.session_state.current_user = None
    st.session_state.saved_ids = []
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False