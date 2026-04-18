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
    "top_cuisines": [],
    "craving_preferences": [],
    "price_comfort_level": "$$",
    "vibes_dining_style": [],
    "dietary_restrictions": [],
    "adventurousness": 3,
    "travel_willingness": "Short commute (10–20 min / ~1 mi)",
    "dining_company": "Small group (3–5)",
    "typical_meals": [],
    "decision_criteria": [],
    "novelty_preference": "mix of both",
    "favorite_dishes": [],
    "loved_restaurants": [],
    "wishlist_restaurants": [],
    "frequent_restaurants": [],
    "aspirational_restaurants": [],
}


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _adapt_to_raw_answers(payload: dict | None) -> dict:
    source = payload if isinstance(payload, dict) else {}

    adapted = {
        "top_cuisines": _clean_list(source.get("top_cuisines", source.get("favorite_cuisines", []))),
        "craving_preferences": _clean_list(source.get("craving_preferences", source.get("cravings", []))),
        "price_comfort_level": str(source.get("price_comfort_level", source.get("price_range", "$$"))).strip() or "$$",
        "vibes_dining_style": _clean_list(source.get("vibes_dining_style", source.get("place_types", []))),
        "dietary_restrictions": _clean_list(source.get("dietary_restrictions", source.get("dietary", []))),
        "adventurousness": source.get("adventurousness", 3),
        "travel_willingness": str(source.get("travel_willingness", "")).strip(),
        "dining_company": str(source.get("dining_company", "Small group (3–5)")).strip() or "Small group (3–5)",
        "typical_meals": _clean_list(source.get("typical_meals", source.get("meals", []))),
        "decision_criteria": _clean_list(source.get("decision_criteria", source.get("decision_style", []))),
        "novelty_preference": str(source.get("novelty_preference", "mix of both")).strip() or "mix of both",
        "favorite_dishes": _clean_list(source.get("favorite_dishes", [])),
        "loved_restaurants": _clean_list(source.get("loved_restaurants", [])),
        "wishlist_restaurants": _clean_list(source.get("wishlist_restaurants", [])),
        "frequent_restaurants": _clean_list(source.get("frequent_restaurants", [])),
        "aspirational_restaurants": _clean_list(source.get("aspirational_restaurants", source.get("dream_restaurants", []))),
    }

    if not adapted["travel_willingness"]:
        legacy_location = str(source.get("usual_location", "")).strip().lower()
        location_to_travel = {
            "near home": "Walking distance (< 10 min / ~0.5 mi)",
            "near school/work": "Short commute (10–20 min / ~1 mi)",
            "will travel for food": "Anywhere in the city",
        }
        adapted["travel_willingness"] = location_to_travel.get(
            legacy_location,
            "Short commute (10–20 min / ~1 mi)",
        )

    try:
        adventurousness = int(adapted["adventurousness"])
    except (TypeError, ValueError):
        adventurousness = 3
    adapted["adventurousness"] = max(1, min(5, adventurousness))

    return adapted


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

    if profile:
        stored_answers = (
            profile.get("raw_answers")
            or profile.get("questionnaire_answers")
            or {}
        )
        st.session_state.questionnaire_answers = _adapt_to_raw_answers(stored_answers)
        st.session_state.onboarding_completed = True


def get_questionnaire_answers() -> dict:
    payload = st.session_state.get("questionnaire_answers", DEFAULT_QUESTIONNAIRE.copy())
    return _adapt_to_raw_answers(payload)


def save_questionnaire_answers(payload: dict) -> None:
    adapted_payload = _adapt_to_raw_answers(payload)
    st.session_state.questionnaire_answers = adapted_payload
    st.session_state.onboarding_completed = True

    current_user = st.session_state.get("current_user")
    if current_user:
        save_user_profile(current_user["username"], adapted_payload)