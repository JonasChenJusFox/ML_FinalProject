"""Onboarding questionnaire UI: collect preferences, prefill from state/DB, save to MongoDB."""

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
    "French",
    "Spanish",
    "Greek",
    "Turkish",
    "Lebanese",
    "Ethiopian",
    "Caribbean",
    "Peruvian",
    "Brazilian",
    "African",
    "Seafood",
    "Steakhouse",
    "Sushi",
    "Ramen",
    "Pizza",
    "Dessert / Bakery",
    "Cafe / Coffee",
    "Other",
]

CRAVINGS = [
    "comfort food",
    "heavy/light",
    "spicy",
    "sweet/dessert",
    "fast/casual",
    "fancy/experimental",
    "savory",
    "healthy",
    "protein-heavy",
    "vegetable-forward",
    "soup/noodles",
    "rice bowls",
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
    "family-friendly",
    "group-friendly",
    "romantic",
    "trendy",
    "classic",
    "music / nightlife",
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
    "Pescatarian",
    "Low-carb",
    "Low-sodium",
    "Keto-friendly",
    "No beef",
    "No pork",
]

MEALS = [
    "breakfast",
    "brunch",
    "lunch",
    "dinner",
    "late night",
    "coffee/snack",
    "dessert",
]

DECISION_STYLE = [
    "ratings",
    "reviews",
    "vibe/atmosphere",
    "convenience",
    "recommendations",
    "price",
    "distance",
    "friend suggestions",
    "social media buzz",
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


def _merge_options_with_existing(options: list[str], selected: list[str]) -> list[str]:
    """
    Preserve previously saved custom values even if not in the base options.
    """
    merged = list(options)
    for item in selected:
        if item not in merged:
            merged.append(item)
    return merged


def _render_multi_choice(
    label: str,
    options: list[str],
    default: list[str],
    *,
    key: str,
) -> list[str]:
    """
    Render a reliable multi-choice control.

    NOTE: We intentionally use multiselect here (instead of pills) because
    pills can be inconsistent in some Streamlit versions inside forms/dialogs.
    """
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

    saved_top_cuisines = answers.get("top_cuisines", [])
    saved_cravings = answers.get("craving_preferences", [])
    saved_vibes = answers.get("vibes_dining_style", [])
    saved_dietary = answers.get("dietary_restrictions", [])
    saved_meals = answers.get("typical_meals", [])
    saved_decision_style = answers.get("decision_criteria", [])

    cuisine_options = _merge_options_with_existing(CUISINES, saved_top_cuisines)
    craving_options = _merge_options_with_existing(CRAVINGS, saved_cravings)
    vibe_options = _merge_options_with_existing(VIBES, saved_vibes)
    dietary_options = _merge_options_with_existing(DIETARY, saved_dietary)
    meal_options = _merge_options_with_existing(MEALS, saved_meals)
    decision_options = _merge_options_with_existing(DECISION_STYLE, saved_decision_style)

    default_top_cuisines = _safe_multiselect_defaults(cuisine_options, saved_top_cuisines)
    default_cravings = _safe_multiselect_defaults(craving_options, saved_cravings)
    default_vibes = _safe_multiselect_defaults(vibe_options, saved_vibes)
    default_dietary = _safe_multiselect_defaults(dietary_options, saved_dietary)
    default_meals = _safe_multiselect_defaults(meal_options, saved_meals)
    default_decision_style = _safe_multiselect_defaults(decision_options, saved_decision_style)

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
            options=cuisine_options,
            default=default_top_cuisines,
            key="onboarding_top_cuisines",
        )
        if len(top_cuisines) > 3:
            st.warning("Please choose up to 3 cuisines.")

        cravings = _render_multi_choice(
            "What kind of food are you most often craving?",
            options=craving_options,
            default=default_cravings,
            key="onboarding_cravings",
        )

        extra_cravings_raw = st.text_input(
            "Other cravings (optional, comma-separated)",
            value="",
            placeholder="brothy, smoky, crunchy",
        )

        price_range = st.selectbox(
            "What's your price comfort level?",
            ["$", "$$", "$$$", "$$$$"],
            index=_safe_index(["$", "$$", "$$$", "$$$$"], default_price_range, default_index=1),
        )

        vibes = _render_multi_choice(
            "Which vibes match your usual dining style?",
            options=vibe_options,
            default=default_vibes,
            key="onboarding_vibes",
        )

        extra_vibes_raw = st.text_input(
            "Other vibes (optional, comma-separated)",
            value="",
            placeholder="minimalist, scenic, speakeasy",
        )

        dietary = _render_multi_choice(
            "Any dietary restrictions or preferences?",
            options=dietary_options,
            default=default_dietary,
            key="onboarding_dietary",
        )

        extra_dietary_raw = st.text_input(
            "Other dietary preferences (optional, comma-separated)",
            value="",
            placeholder="shellfish allergy, low sugar",
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
            options=meal_options,
            default=default_meals,
            key="onboarding_meals",
        )

        extra_meals_raw = st.text_input(
            "Other meal contexts (optional, comma-separated)",
            value="",
            placeholder="post-workout, after class",
        )

        decision_style = _render_multi_choice(
            "How do you usually choose restaurants?",
            options=decision_options,
            default=default_decision_style,
            key="onboarding_decision_style",
        )

        extra_decision_style_raw = st.text_input(
            "Other decision factors (optional, comma-separated)",
            value="",
            placeholder="wait time, reservation availability",
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

            extra_cravings = parse_comma_tags(extra_cravings_raw)
            extra_vibes = parse_comma_tags(extra_vibes_raw)
            extra_dietary = parse_comma_tags(extra_dietary_raw)
            extra_meals = parse_comma_tags(extra_meals_raw)
            extra_decision_style = parse_comma_tags(extra_decision_style_raw)

            payload = {
                "top_cuisines": top_cuisines,
                "craving_preferences": list(dict.fromkeys(cravings + extra_cravings)),
                "price_comfort_level": price_range,
                "vibes_dining_style": list(dict.fromkeys(vibes + extra_vibes)),
                "dietary_restrictions": list(dict.fromkeys(dietary + extra_dietary)),
                "adventurousness": adventurousness,
                "travel_willingness": travel_willingness,
                "dining_company": dining_company,
                "typical_meals": list(dict.fromkeys(meals + extra_meals)),
                "decision_criteria": list(dict.fromkeys(decision_style + extra_decision_style)),
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
