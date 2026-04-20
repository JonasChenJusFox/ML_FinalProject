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
    """Build embedding-ready profile text from questionnaire answers."""
    answers = raw_answers if isinstance(raw_answers, dict) else {}
    normalized = normalize_answers(answers)

    parts: list[str] = []

    for key in [
        "top_cuisines",
        "craving_preferences",
        "vibes_dining_style",
        "dietary_restrictions",
        "typical_meals",
        "decision_criteria",
        "favorite_dishes",
        "loved_restaurants",
        "wishlist_restaurants",
        "frequent_restaurants",
        "aspirational_restaurants",
    ]:
        value = answers.get(key, [])
        if isinstance(value, list) and value:
            parts.append(f"{key}: " + ", ".join(str(item).strip() for item in value if str(item).strip()))

    price = str(answers.get("price_comfort_level", "$$")).strip() or "$$"
    travel = str(answers.get("travel_willingness", "")).strip()
    company = str(answers.get("dining_company", "")).strip()
    novelty = str(answers.get("novelty_preference", "")).strip()
    adventurousness = answers.get("adventurousness", 3)

    parts.append(f"price comfort: {price}")
    if travel:
        parts.append(f"travel willingness: {travel}")
    if company:
        parts.append(f"dining company: {company}")
    if novelty:
        parts.append(f"novelty preference: {novelty}")
    parts.append(f"adventurousness: {adventurousness}")

    affinity_terms = normalized.get("restaurant_affinity_terms", [])
    if affinity_terms:
        parts.append("restaurant affinity: " + ", ".join(affinity_terms))

    return " | ".join(part for part in parts if part).strip()