"""Minimal user profile modeling utilities based on onboarding questionnaire."""

from __future__ import annotations


PRICE_TO_LEVEL = {
    "$": 1,
    "$$": 2,
    "$$$": 3,
    "$$$$": 4,
}

TRAVEL_TO_MAX_KM = {
    "Walking distance (< 10 min / ~0.5 mi)": 0.8,
    "Short commute (10–20 min / ~1 mi)": 1.6,
    "Across the neighborhood (20–35 min)": 5.0,
    "Anywhere in the city": 20.0,
}

NOVELTY_TO_LEVEL = {
    "stick to what i know": 0.1,
    "mix of both": 0.5,
    "try new things": 0.9,
}


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def normalize_answers(raw_answers: dict) -> dict:
    """Normalize questionnaire raw answers into lightweight structured user features."""
    answers = raw_answers if isinstance(raw_answers, dict) else {}

    top_cuisines = _clean_list(answers.get("top_cuisines", []))
    cravings = _clean_list(answers.get("craving_preferences", []))
    vibes = _clean_list(answers.get("vibes_dining_style", []))
    dietary = _clean_list(answers.get("dietary_restrictions", []))
    meals = _clean_list(answers.get("typical_meals", []))
    decision = _clean_list(answers.get("decision_criteria", []))
    dishes = _clean_list(answers.get("favorite_dishes", []))

    loved = _clean_list(answers.get("loved_restaurants", []))
    wishlist = _clean_list(answers.get("wishlist_restaurants", []))
    frequent = _clean_list(answers.get("frequent_restaurants", []))
    aspirational = _clean_list(answers.get("aspirational_restaurants", []))

    novelty = str(answers.get("novelty_preference", "")).strip().lower()
    price_symbol = str(answers.get("price_comfort_level", "$$")).strip() or "$$"
    adventurousness = answers.get("adventurousness", 3)

    try:
        adventurousness_value = int(adventurousness)
    except (TypeError, ValueError):
        adventurousness_value = 3
    adventurousness_value = max(1, min(5, adventurousness_value))

    travel = str(answers.get("travel_willingness", "")).strip()
    if travel not in TRAVEL_TO_MAX_KM:
        travel = "Short commute (10–20 min / ~1 mi)"

    return {
        "cuisine_pref": [item.lower() for item in top_cuisines],
        "craving_tags": [item.lower() for item in cravings],
        "price_level": {
            "symbol": price_symbol,
            "numeric": PRICE_TO_LEVEL.get(price_symbol, 2),
        },
        "vibe_tags": [item.lower() for item in vibes],
        "dietary_tags": [item.lower() for item in dietary if item.lower() != "none"],
        "adventure_level": round((adventurousness_value - 1) / 4, 3),
        "max_travel_km": TRAVEL_TO_MAX_KM.get(travel, 1.6),
        "company_tags": [str(answers.get("dining_company", "")).strip().lower()] if str(answers.get("dining_company", "")).strip() else [],
        "meal_tags": [item.lower() for item in meals],
        "decision_weights": {item.lower(): 1.0 for item in decision},
        "novelty_level": NOVELTY_TO_LEVEL.get(novelty, 0.5),
        "dish_tags": [item.lower() for item in dishes],
        "restaurant_affinity_terms": [
            item.lower()
            for item in (loved + frequent + wishlist + aspirational)
        ],
    }


def build_profile_text(raw_answers: dict) -> str:
    """Build embedding-ready profile text from normalized questionnaire signals."""
    answers = raw_answers if isinstance(raw_answers, dict) else {}
    normalized = normalize_answers(answers)

    def _phrase(items: list[str]) -> str:
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"

    top_cuisines = _phrase(normalized.get("cuisine_pref", []))
    craving_preferences = _phrase(normalized.get("craving_tags", []))
    dietary_restrictions = _phrase(normalized.get("dietary_tags", []))
    typical_meals = _phrase(normalized.get("meal_tags", []))
    favorite_dishes = _phrase(normalized.get("dish_tags", []))
    dining_company = _phrase(normalized.get("company_tags", []))
    decision_criteria = _phrase(list((normalized.get("decision_weights", {}) or {}).keys()))
    restaurant_affinity_terms = _phrase(normalized.get("restaurant_affinity_terms", []))

    price_level_numeric = normalized.get("price_level", {}).get("numeric", 2)
    travel_willingness_km = normalized.get("max_travel_km", 1.6)
    novelty_preference = normalized.get("novelty_level", 0.5)
    adventurousness = normalized.get("adventure_level", 0.5)
    price_text = {
        1: "budget-friendly",
        2: "moderate",
        3: "expensive",
        4: "luxury",
    }.get(int(price_level_numeric), "moderate")

    if novelty_preference >= 0.8:
        novelty_text = "often seeks new places and cuisines"
    elif novelty_preference <= 0.2:
        novelty_text = "usually prefers familiar choices"
    else:
        novelty_text = "likes a mix of familiar spots and new experiences"

    if adventurousness >= 0.75:
        adventure_text = "is highly adventurous with food choices"
    elif adventurousness <= 0.25:
        adventure_text = "prefers safer, predictable food choices"
    else:
        adventure_text = "is moderately adventurous with food choices"

    parts: list[str] = []
    if top_cuisines:
        parts.append(f"Preferred cuisines include {top_cuisines}.")
    if craving_preferences:
        parts.append(f"Common cravings include {craving_preferences}.")
    if favorite_dishes:
        parts.append(f"Favorite dishes include {favorite_dishes}.")
    if dietary_restrictions:
        parts.append(f"Dietary requirements: {dietary_restrictions}.")

    parts.append(
        f"Price preference is {price_text}, and typical travel tolerance is about {travel_willingness_km:.1f} km."
    )

    if dining_company:
        parts.append(f"Usually dines with {dining_company}.")
    if typical_meals:
        parts.append(f"Typical meal context includes {typical_meals}.")
    if decision_criteria:
        parts.append(f"Main decision priorities are {decision_criteria}.")

    parts.append(f"The user {novelty_text} and {adventure_text}.")

    if restaurant_affinity_terms:
        parts.append(f"Restaurant affinity signals include {restaurant_affinity_terms}.")

    return " ".join(part.strip() for part in parts if part.strip())