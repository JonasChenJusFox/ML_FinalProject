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

from frontend.auth import close_questionnaire_modal
from frontend.user_profile_state import (
    get_questionnaire_answers,
    save_questionnaire_answers,
)
from integration.price_utils import PRICE_LABELS

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
QUESTIONNAIRE_PRICE_OPTIONS = PRICE_LABELS
TOP_CUISINE_NONE_OPTION = "None"


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


def _safe_top_cuisine_default(selected: list[str], index: int) -> str:
    """
    Return the default value for one of the three cuisine pickers.
    """
    if index < len(selected):
        return selected[index]
    return TOP_CUISINE_NONE_OPTION


def _normalize_top_cuisine_selection(selected_items: list[str]) -> list[str]:
    """
    Remove blanks while preserving user order.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for item in selected_items:
        if not item or item == TOP_CUISINE_NONE_OPTION or item in seen:
            continue
        normalized.append(item)
        seen.add(item)
    return normalized


def _normalize_multi_choice_selection(selected_items: list[str]) -> list[str]:
    """
    Remove duplicates while preserving order.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for item in selected_items:
        if not item or item in seen:
            continue
        normalized.append(item)
        seen.add(item)
    return normalized


def _render_checkbox_grid(
    *,
    label: str,
    options: list[str],
    selected: list[str],
    key_prefix: str,
    columns: int = 3,
) -> list[str]:
    """
    Render a stable multi-select UI without dropdown popovers.
    """
    st.markdown(f"**{label}**")
    cols = st.columns(columns)
    chosen: list[str] = []
    for idx, option in enumerate(options):
        with cols[idx % columns]:
            checked = st.checkbox(
                option,
                value=option in selected,
                key=f"{key_prefix}_{idx}",
            )
            if checked:
                chosen.append(option)
    return _normalize_multi_choice_selection(chosen)


def render_onboarding_form(*, show_header: bool = True) -> None:
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

    default_price_range = answers.get("price_comfort_level", "moderate")
    default_travel = answers.get("travel_willingness", "Short commute (10–20 min / ~1 mi)")
    default_dining_company = answers.get("dining_company", "Small group (3–5)")
    default_novelty = answers.get("novelty_preference", "mix of both")
    default_adventurousness = int(answers.get("adventurousness", 3) or 3)

    default_favorite_dishes = ", ".join(answers.get("favorite_dishes", []))
    default_loved_restaurants = ", ".join(answers.get("loved_restaurants", []))
    default_wishlist_restaurants = ", ".join(answers.get("wishlist_restaurants", []))
    default_frequent_restaurants = ", ".join(answers.get("frequent_restaurants", []))
    default_aspirational_restaurants = ", ".join(answers.get("aspirational_restaurants", []))

    if show_header:
        st.subheader("User Onboarding Questionnaire")
    st.markdown("<div class='nb-recommendation-form-anchor'></div>", unsafe_allow_html=True)

    with st.form("user_onboarding_form"):
        st.markdown("**What are your top 3 cuisines?**")
        st.caption("Pick up to 3 cuisines. Leave any extra slot as None.")
        cuisine_options = [TOP_CUISINE_NONE_OPTION, *CUISINES]
        cuisine_col_1, cuisine_col_2, cuisine_col_3 = st.columns(3)
        with cuisine_col_1:
            top_cuisine_1 = st.selectbox(
                "Cuisine 1",
                cuisine_options,
                index=_safe_index(
                    cuisine_options,
                    _safe_top_cuisine_default(default_top_cuisines, 0),
                ),
                key="questionnaire_top_cuisine_1",
            )
        with cuisine_col_2:
            top_cuisine_2 = st.selectbox(
                "Cuisine 2",
                cuisine_options,
                index=_safe_index(
                    cuisine_options,
                    _safe_top_cuisine_default(default_top_cuisines, 1),
                ),
                key="questionnaire_top_cuisine_2",
            )
        with cuisine_col_3:
            top_cuisine_3 = st.selectbox(
                "Cuisine 3",
                cuisine_options,
                index=_safe_index(
                    cuisine_options,
                    _safe_top_cuisine_default(default_top_cuisines, 2),
                ),
                key="questionnaire_top_cuisine_3",
            )
        top_cuisines = _normalize_top_cuisine_selection(
            [top_cuisine_1, top_cuisine_2, top_cuisine_3]
        )

        cravings = _render_checkbox_grid(
            label="What kind of food are you most often craving?",
            options=CRAVINGS,
            selected=default_cravings,
            key_prefix="questionnaire_cravings",
        )

        price_range = st.selectbox(
            "What's your price comfort level?",
            QUESTIONNAIRE_PRICE_OPTIONS,
            index=_safe_index(QUESTIONNAIRE_PRICE_OPTIONS, default_price_range, default_index=1),
        )

        vibes = _render_checkbox_grid(
            label="Which vibes match your usual dining style?",
            options=VIBES,
            selected=default_vibes,
            key_prefix="questionnaire_vibes",
        )

        dietary = _render_checkbox_grid(
            label="Any dietary restrictions or preferences?",
            options=DIETARY,
            selected=default_dietary,
            key_prefix="questionnaire_dietary",
        )
        if "None" in dietary and len(dietary) > 1:
            dietary = ["None"]

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

        meals = _render_checkbox_grid(
            label="What meals do you usually go out for?",
            options=MEALS,
            selected=default_meals,
            key_prefix="questionnaire_meals",
        )

        decision_style = _render_checkbox_grid(
            label="How do you usually choose restaurants?",
            options=DECISION_STYLE,
            selected=default_decision_style,
            key_prefix="questionnaire_decision_style",
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
            raw_top_cuisines = [top_cuisine_1, top_cuisine_2, top_cuisine_3]
            if len(top_cuisines) != len(
                [
                    item
                    for item in raw_top_cuisines
                    if item and item != TOP_CUISINE_NONE_OPTION
                ]
            ):
                st.error("Please choose up to 3 different cuisines.")
                return

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
            close_questionnaire_modal()
            st.session_state.page = "Home"
            st.rerun()
