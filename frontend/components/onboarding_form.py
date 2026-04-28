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
    "Japanese",
    "Chinese",
    "Korean",
    "Italian",
    "Mexican",
    "Indian",
    "Thai",
    "American / Burgers",
    "Mediterranean / Middle Eastern",
    "Vietnamese",
    "Other",
]

CRAVINGS = [
    "comfort food",
    "heavy/light",
    "spicy",
    "sweet/dessert",
    "fast/casual",
    "fancy/experimental",
]
VIBES = [
    "cozy / intimate",
    "lively / buzzy",
    "quiet / work-friendly",
    "date night",
    "casual hangout",
    "quick bite / grab-and-go",
    "outdoor / terrace",
    "late night",
]

DIETARY = [
    "None",
    "Vegetarian",
    "Vegan",
    "Halal",
    "Kosher",
    "Gluten-free",
    "Nut allergy",
    "Dairy-free",
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

TRAVEL_WILLINGNESS_OPTIONS = [
    "Walking distance (< 10 min / ~0.5 mi)",
    "Short commute (10–20 min / ~1 mi)",
    "Across the neighborhood (20–35 min)",
    "Anywhere in the city",
]

DINING_COMPANY_OPTIONS = [
    "Solo",
    "Partner / couple",
    "Small group (3–5)",
    "Large group (6+)",
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


def _render_multi_choice(
    label: str,
    options: list[str],
    default: list[str],
    *,
    key: str,
) -> list[str]:
    """
    Render a cleaner multi-choice control. Use st.pills when available,
    and fall back to st.multiselect for older Streamlit versions.
    """
    if hasattr(st, "pills"):
        values = st.pills(
            label,
            options,
            default=default,
            selection_mode="multi",
            key=key,
        )
        return list(values or [])

    return st.multiselect(
        label,
        options,
        default=default,
        key=key,
    )


def render_onboarding_form() -> None:
    """
    Render the onboarding questionnaire with database-backed prefilled defaults.
    """
    answers = get_questionnaire_answers()

    default_top_cuisines = _safe_multiselect_defaults(
        CUISINES,
        answers.get("top_cuisines", []),
    )
    default_cravings = _safe_multiselect_defaults(
        CRAVINGS,
        answers.get("craving_preferences", []),
    )
    default_vibes = _safe_multiselect_defaults(
        VIBES,
        answers.get("vibes_dining_style", []),
    )
    default_dietary = _safe_multiselect_defaults(
        DIETARY,
        answers.get("dietary_restrictions", []),
    )
    default_meals = _safe_multiselect_defaults(
        MEALS,
        answers.get("typical_meals", []),
    )
    default_decision_style = _safe_multiselect_defaults(
        DECISION_STYLE,
        answers.get("decision_criteria", []),
    )

    default_price_range = answers.get("price_comfort_level", "$$")
    default_travel = answers.get("travel_willingness", "Short commute (10–20 min / ~1 mi)")
    default_dining_company = answers.get("dining_company", "Small group (3–5)")
    default_novelty = answers.get("novelty_preference", "mix of both")
    default_adventurousness = int(answers.get("adventurousness", 3) or 3)

    default_favorite_dishes = ", ".join(answers.get("favorite_dishes", []))
    default_loved_restaurants = ", ".join(answers.get("loved_restaurants", []))
    default_wishlist_restaurants = ", ".join(answers.get("wishlist_restaurants", []))
    default_frequent_restaurants = ", ".join(answers.get("frequent_restaurants", []))
    default_aspirational_restaurants = ", ".join(answers.get("aspirational_restaurants", []))

    st.markdown("<div class='nb-onboarding-anchor'></div>", unsafe_allow_html=True)
    st.subheader("User Onboarding Questionnaire")

    with st.form("user_onboarding_form"):
        top_cuisines = _render_multi_choice(
            "What are your top 3 cuisines?",
            options=CUISINES,
            default=default_top_cuisines,
            key="onboarding_top_cuisines",
        )
        if len(top_cuisines) > 3:
            st.warning("Please choose up to 3 cuisines.")

        cravings = _render_multi_choice(
            "What kind of food are you most often craving?",
            options=CRAVINGS,
            default=default_cravings,
            key="onboarding_cravings",
        )

        price_range = st.selectbox(
            "What's your price comfort level?",
            ["$", "$$", "$$$", "$$$$"],
            index=_safe_index(["$", "$$", "$$$", "$$$$"], default_price_range, default_index=1),
        )

        vibes = _render_multi_choice(
            "Which vibes match your usual dining style?",
            options=VIBES,
            default=default_vibes,
            key="onboarding_vibes",
        )

        dietary = _render_multi_choice(
            "Any dietary restrictions or preferences?",
            options=DIETARY,
            default=default_dietary,
            key="onboarding_dietary",
        )

        adventurousness = st.slider(
            "How adventurous are you with new food?",
            min_value=1,
            max_value=5,
            value=max(1, min(5, default_adventurousness)),
            step=1,
        )

        travel_willingness = st.radio(
            "How far are you willing to travel for a meal?",
            TRAVEL_WILLINGNESS_OPTIONS,
            index=_safe_index(TRAVEL_WILLINGNESS_OPTIONS, default_travel, default_index=1),
        )

        dining_company = st.radio(
            "Who do you usually eat out with?",
            DINING_COMPANY_OPTIONS,
            index=_safe_index(DINING_COMPANY_OPTIONS, default_dining_company, default_index=2),
        )

        meals = _render_multi_choice(
            "What meals do you usually go out for?",
            options=MEALS,
            default=default_meals,
            key="onboarding_meals",
        )

        decision_style = _render_multi_choice(
            "How do you usually choose restaurants?",
            options=DECISION_STYLE,
            default=default_decision_style,
            key="onboarding_decision_style",
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

        loved_restaurants_raw = st.text_area(
            "Name up to 5 NYC restaurants you've loved",
            value=default_loved_restaurants,
            placeholder="Restaurant A, Restaurant B, Restaurant C",
        )

        wishlist_restaurants_raw = st.text_area(
            "Any restaurants on your wishlist?",
            value=default_wishlist_restaurants,
            placeholder="Wishlist spot 1, Wishlist spot 2",
        )

        frequent_restaurants_raw = st.text_area(
            "Pick 3 restaurants you like to frequent in NYC",
            value=default_frequent_restaurants,
            placeholder="Ippudo, Joe's Pizza, Xi'an Famous Foods",
        )

        aspirational_restaurants_raw = st.text_area(
            "Pick 3 restaurants you would frequent if you had unlimited budget in NYC",
            value=default_aspirational_restaurants,
            placeholder="Le Bernardin, Atomix, Masa",
        )

        submitted = st.form_submit_button("Save profile", use_container_width=True)

        if submitted:
            if len(top_cuisines) > 3:
                st.error("You can select at most 3 cuisines.")
                st.stop()
            payload = {
                "top_cuisines": top_cuisines,
                "craving_preferences": cravings,
                "price_comfort_level": price_range,
                "vibes_dining_style": vibes,
                "dietary_restrictions": dietary,
                "adventurousness": adventurousness,
                "travel_willingness": travel_willingness,
                "dining_company": dining_company,
                "typical_meals": meals,
                "decision_criteria": decision_style,
                "novelty_preference": novelty_preference,
                "favorite_dishes": parse_comma_tags(favorite_dishes_raw),
                "loved_restaurants": parse_comma_tags(loved_restaurants_raw),
                "wishlist_restaurants": parse_comma_tags(wishlist_restaurants_raw),
                "frequent_restaurants": parse_comma_tags(frequent_restaurants_raw),
                "aspirational_restaurants": parse_comma_tags(aspirational_restaurants_raw),
            }

            save_questionnaire_answers(payload)
            st.success("Profile saved.")
            st.session_state.editing_questionnaire = False
            st.session_state.show_post_signup_questionnaire = False
            st.session_state.page = "Profile"
            st.rerun()
