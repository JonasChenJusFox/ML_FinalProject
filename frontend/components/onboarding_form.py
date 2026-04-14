"""
frontend/components/onboarding_form.py
Owner: Jonas Chen

Responsibilities:
- Renders the user onboarding questionnaire form
- Collects structured preference inputs for recommendation
- Prefills questionnaire answers from session state / MongoDB-loaded profile data
- Saves questionnaire answers into session state and MongoDB
- Supports editing and resubmitting profile answers over time
"""

from __future__ import annotations

import streamlit as st

from frontend.user_profile_state import (
    get_questionnaire_answers,
    save_questionnaire_answers,
)

CUISINES = [
    "Italian",
    "Japanese",
    "Chinese",
    "Korean",
    "Thai",
    "Mexican",
    "Indian",
    "Mediterranean",
    "French",
    "American",
    "Middle Eastern",
]

CRAVINGS = [
    "comfort food",
    "heavy",
    "light",
    "spicy",
    "sweet/dessert",
    "fast/casual",
    "fancy/experimental",
]

PLACE_TYPES = [
    "cozy",
    "trendy",
    "quiet",
    "lively",
    "romantic",
    "good for groups",
    "casual",
    "aesthetic/instagram",
]

DIETARY = [
    "none",
    "vegetarian",
    "vegan",
    "Halal",
    "gluten-free",
    "dairy-free",
]

MEALS = [
    "breakfast",
    "brunch",
    "lunch",
    "dinner",
    "late night",
]

DECISION_STYLE = [
    "ratings",
    "review",
    "vibe/atmosphere",
    "convenience",
    "recommendations",
]

LOCATION_OPTIONS = [
    "near home",
    "near school/work",
    "will travel for food",
]

NOVELTY_OPTIONS = [
    "stick to what i know",
    "mix of both",
    "try new things",
]


def parse_comma_tags(raw: str) -> list[str]:
    """
    Convert comma-separated user input into a clean list of strings.
    """
    return [item.strip() for item in raw.split(",") if item.strip()]


def _safe_index(options: list[str], value: str, default_index: int = 0) -> int:
    """
    Return a safe select/radio index from a stored value.
    """
    if value in options:
        return options.index(value)
    return default_index


def _safe_multiselect_defaults(options: list[str], selected: list[str]) -> list[str]:
    """
    Keep only valid defaults that still exist in the current options list.
    """
    return [item for item in selected if item in options]


def render_onboarding_form() -> None:
    """
    Render the onboarding questionnaire with database-backed prefilled defaults.
    """
    answers = get_questionnaire_answers()

    default_favorite_cuisines = _safe_multiselect_defaults(
        CUISINES,
        answers.get("favorite_cuisines", []),
    )
    default_cravings = _safe_multiselect_defaults(
        CRAVINGS,
        answers.get("cravings", []),
    )
    default_place_types = _safe_multiselect_defaults(
        PLACE_TYPES,
        answers.get("place_types", []),
    )
    default_dietary = _safe_multiselect_defaults(
        DIETARY,
        answers.get("dietary", []),
    )
    default_meals = _safe_multiselect_defaults(
        MEALS,
        answers.get("meals", []),
    )
    default_decision_style = _safe_multiselect_defaults(
        DECISION_STYLE,
        answers.get("decision_style", []),
    )

    default_price_range = answers.get("price_range", "$$")
    default_usual_location = answers.get("usual_location", "near school/work")
    default_novelty = answers.get("novelty_preference", "mix of both")

    default_favorite_dishes = ", ".join(answers.get("favorite_dishes", []))
    default_frequent_restaurants = ", ".join(answers.get("frequent_restaurants", []))
    default_dream_restaurants = ", ".join(answers.get("dream_restaurants", []))

    st.subheader("User Onboarding Questionnaire")

    with st.form("user_onboarding_form"):
        favorite_cuisines = st.multiselect(
            "What cuisines do you usually enjoy? (select up to 5)",
            CUISINES,
            default=default_favorite_cuisines,
            max_selections=5,
        )

        cravings = st.multiselect(
            "What kind of food are you most often craving?",
            CRAVINGS,
            default=default_cravings,
        )

        price_range = st.selectbox(
            "What price range do you usually go for?",
            ["$", "$$", "$$$", "$$$$"],
            index=_safe_index(["$", "$$", "$$$", "$$$$"], default_price_range, default_index=1),
        )

        place_types = st.multiselect(
            "What kind of places do you like? (multi-select, 3-5)",
            PLACE_TYPES,
            default=default_place_types,
        )

        dietary = st.multiselect(
            "Any dietary preferences or restrictions?",
            DIETARY,
            default=default_dietary,
        )

        usual_location = st.radio(
            "Where do you usually eat?",
            LOCATION_OPTIONS,
            index=_safe_index(LOCATION_OPTIONS, default_usual_location, default_index=1),
        )

        meals = st.multiselect(
            "What meals do you usually go out for?",
            MEALS,
            default=default_meals,
        )

        decision_style = st.multiselect(
            "How do you usually choose restaurants?",
            DECISION_STYLE,
            default=default_decision_style,
        )

        novelty_preference = st.radio(
            "Do you prefer:",
            NOVELTY_OPTIONS,
            index=_safe_index(NOVELTY_OPTIONS, default_novelty, default_index=1),
        )

        favorite_dishes_raw = st.text_area(
            "Pick a few dishes you love (free text or comma-separated tags)",
            value=default_favorite_dishes,
            placeholder="ramen, tiramisu, hotpot, tacos",
        )

        frequent_restaurants_raw = st.text_area(
            "Pick 3 restaurants you like to frequent in NYC",
            value=default_frequent_restaurants,
            placeholder="Ippudo, Joe's Pizza, Xi'an Famous Foods",
        )

        dream_restaurants_raw = st.text_area(
            "Pick 3 restaurants you would frequent if you had unlimited budget in NYC",
            value=default_dream_restaurants,
            placeholder="Le Bernardin, Atomix, Masa",
        )

        submitted = st.form_submit_button("Save profile", use_container_width=True)

        if submitted:
            payload = {
                "favorite_cuisines": favorite_cuisines,
                "cravings": cravings,
                "price_range": price_range,
                "place_types": place_types,
                "dietary": dietary,
                "usual_location": usual_location,
                "meals": meals,
                "decision_style": decision_style,
                "novelty_preference": novelty_preference,
                "favorite_dishes": parse_comma_tags(favorite_dishes_raw),
                "frequent_restaurants": parse_comma_tags(frequent_restaurants_raw),
                "dream_restaurants": parse_comma_tags(dream_restaurants_raw),
            }

            save_questionnaire_answers(payload)
            st.success("Profile saved.")
            st.session_state.editing_questionnaire = False
            st.session_state.page = "Recommendation"
            st.rerun()