"""
frontend/user_profile_state.py
Owner: Jonas Chen

Responsibilities:
- Stores onboarding questionnaire answers in Streamlit session state
- Loads questionnaire answers from MongoDB after login
- Saves profile data to MongoDB when the questionnaire is submitted
- Supports future migration to richer user profile storage
"""

from __future__ import annotations

import streamlit as st

from integration.user_repo import get_user_profile, save_user_profile

DEFAULT_QUESTIONNAIRE = {
    "favorite_cuisines": [],
    "cravings": [],
    "price_range": "$$",
    "place_types": [],
    "dietary": [],
    "usual_location": "near school/work",
    "meals": [],
    "decision_style": [],
    "novelty_preference": "mix of both",
    "favorite_dishes": [],
    "frequent_restaurants": [],
    "dream_restaurants": [],
}


def init_user_profile_state() -> None:
    if "questionnaire_answers" not in st.session_state:
        st.session_state.questionnaire_answers = DEFAULT_QUESTIONNAIRE.copy()

    if "onboarding_completed" not in st.session_state:
        st.session_state.onboarding_completed = False

    current_user = st.session_state.get("current_user")
    if not current_user:
        return

    username = current_user.get("username")
    profile = get_user_profile(username)

    if profile and "questionnaire_answers" in profile:
        st.session_state.questionnaire_answers = profile["questionnaire_answers"]
        st.session_state.onboarding_completed = True


def get_questionnaire_answers() -> dict:
    return st.session_state.get("questionnaire_answers", DEFAULT_QUESTIONNAIRE.copy())


def save_questionnaire_answers(payload: dict) -> None:
    st.session_state.questionnaire_answers = payload
    st.session_state.onboarding_completed = True

    current_user = st.session_state.get("current_user")
    if current_user:
        save_user_profile(current_user["username"], payload)