"""Restaurant ranking logic for NearBite."""

from __future__ import annotations

import math
from typing import Any

from recommendation.utils import clamp, distance_score as _distance_score, price_level_value, safe_log1p, to_float

DEFAULT_RANKING_WEIGHTS: dict[str, float] = {
    "semantic": 0.60,
    "rating": 0.10,
    "popularity": 0.05,
    "price_match": 0.05,
    "distance": 0.20,
}

VEGAN_RELATED_TERMS: tuple[str, ...] = (
    "vegan",
    "plant-based",
    "plant based",
    "vegetarian",
    "dairy-free",
    "dairy free",
    "meatless",
)

DIETARY_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "vegan": VEGAN_RELATED_TERMS,
    "plant-based": VEGAN_RELATED_TERMS,
    "plant based": VEGAN_RELATED_TERMS,
    "vegetarian": ("vegetarian", "vegan", "plant-based", "plant based", "meatless"),
    "dairy-free": ("dairy-free", "dairy free", "vegan", "plant-based", "plant based"),
    "dairy free": ("dairy-free", "dairy free", "vegan", "plant-based", "plant based"),
    "meatless": ("meatless", "vegetarian", "vegan", "plant-based", "plant based"),
    "gluten-free": ("gluten-free", "gluten free", "glutenfree", "celiac", "wheat-free", "wheat free"),
    "halal": ("halal", "zabiha", "zabihah", "dhabiha"),
    "kosher": ("kosher", "glatt kosher", "certified kosher"),
}

BOOST_WEIGHTS: dict[str, float] = {
    "dietary": 0.80,
    "location": 0.25,
    "cuisine": 0.40,
    "price": 0.30,
    "vibe": 0.30,
    "meal_type": 0.10,
}


def _restaurant_search_text(restaurant: dict[str, Any]) -> str:
    """Build a lightweight searchable text from precomputed fields without looping through raw reviews."""
    parts: list[str] = []

    for key in (
        "name",
        "neighborhood",
        "borough",
        "embedding_text",
        "document",
        "summary",
        "description",
        "review_snippet",
    ):
        value = restaurant.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip().lower())

    for list_key in ("categories", "tags", "vibes"):
        values = restaurant.get(list_key, [])
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    parts.extend(
                        str(value.get(key, "")).strip().lower()
                        for key in ("title", "name", "alias", "text")
                        if str(value.get(key, "")).strip()
                    )
                elif str(value).strip():
                    parts.append(str(value).strip().lower())

    return " ".join(parts)


def _normalize_dietary_preferences(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [values] if values else []

    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip().lower().replace("_", "-")
        if text and text not in {"none", "no restriction", "no restrictions"}:
            normalized.append(text)
    return normalized


def _as_clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [values] if values else []
    return [
        str(value).strip().lower().replace("_", " ")
        for value in values
        if str(value or "").strip()
    ]


def _text_matches_any(text: str, values: list[str]) -> bool:
    padded_text = f" {text.lower().replace('-', ' ')} "
    for value in values:
        normalized = value.strip().lower().replace("-", " ")
        if normalized and f" {normalized} " in padded_text:
            return True
    return False


def compute_dietary_preference_boost(
    restaurant: dict[str, Any],
    active_filters: dict[str, Any] | None = None,
) -> float:
    """Return a strong soft dietary boost without excluding non-matches."""
    if not active_filters:
        return 0.0

    dietary_preferences = _normalize_dietary_preferences(active_filters.get("dietary", []))
    if not dietary_preferences:
        return 0.0

    text = _restaurant_search_text(restaurant)
    if not text:
        return 0.0

    boost = 0.0
    for preference in dietary_preferences:
        aliases = DIETARY_TERM_ALIASES.get(preference, (preference,))
        if _text_matches_any(text, list(aliases)):
            boost += 0.34 if preference in {"vegan", "plant-based", "plant based"} else 0.24

    return min(0.42, boost)


def compute_location_preference_boost(
    restaurant: dict[str, Any],
    active_filters: dict[str, Any] | None = None,
) -> float:
    if not active_filters:
        return 0.0

    has_location_intent = bool(
        active_filters.get("location")
        or active_filters.get("origin_lat") is not None
        or active_filters.get("origin_lon") is not None
        or active_filters.get("nearby")
    )
    if not has_location_intent:
        return 0.0

    return 0.14 * compute_distance_penalty(restaurant.get("distance_km"))


def compute_cuisine_preference_boost(
    restaurant: dict[str, Any],
    active_filters: dict[str, Any] | None = None,
) -> float:
    if not active_filters:
        return 0.0

    cuisines = _as_clean_list(active_filters.get("cuisines"))
    if not cuisines:
        return 0.0

    text = _restaurant_search_text(restaurant)
    return 0.12 if _text_matches_any(text, cuisines) else 0.0


def compute_vibe_preference_boost(
    restaurant: dict[str, Any],
    active_filters: dict[str, Any] | None = None,
) -> float:
    if not active_filters:
        return 0.0

    values = _as_clean_list(active_filters.get("vibe"))
    if not values:
        return 0.0

    text = _restaurant_search_text(restaurant)
    return 0.50 if _text_matches_any(text, values) else 0.0


def compute_meal_type_boost(
    restaurant: dict[str, Any],
    active_filters: dict[str, Any] | None = None,
) -> float:
    if not active_filters:
        return 0.0

    values = _as_clean_list(active_filters.get("meal_type"))
    if not values:
        return 0.0

    text = _restaurant_search_text(restaurant)
    return 0.04 if _text_matches_any(text, values) else 0.0


def _normalize_price_level(value: Any) -> float:
    """Normalize price labels or dollar strings to a comparable level."""
    if value is None:
        return 0.0

    text = str(value).strip().lower()
    if not text:
        return 0.0

    named_levels = {
        "cheap": 1.0,
        "moderate": 2.0,
        "expensive": 3.0,
        "luxury": 4.0,
        "unknown": 0.0,
    }
    if text in named_levels:
        return named_levels[text]

    dollar_level = price_level_value(text)
    if dollar_level > 0.0:
        return min(4.0, dollar_level)

    numeric_level = to_float(text, 0.0)
    if numeric_level > 0.0:
        return min(4.0, numeric_level)

    return 0.0


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity using plain Python math."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = 0.0
    norm1_squared = 0.0
    norm2_squared = 0.0

    for value1, value2 in zip(vec1, vec2):
        dot_product += value1 * value2
        norm1_squared += value1 * value1
        norm2_squared += value2 * value2

    if norm1_squared <= 0.0 or norm2_squared <= 0.0:
        return 0.0

    return dot_product / (math.sqrt(norm1_squared) * math.sqrt(norm2_squared))


def fuse_vectors(
    query_vec: list[float],
    user_vec: list[float] | None,
    alpha: float = 0.3,
) -> list[float]:
    """Fuse query and user vectors where ``alpha`` is user-preference weight."""
    if user_vec is None or len(query_vec) != len(user_vec):
        return list(query_vec)

    alpha_value = clamp(alpha, 0.0, 1.0)
    return [
        (1.0 - alpha_value) * query_value + alpha_value * user_value
        for query_value, user_value in zip(query_vec, user_vec)
    ]


def compute_semantic_score(fused_vec: list[float], restaurant_vec: list[float]) -> float:
    """Return the semantic similarity between the fused query vector and a restaurant embedding."""
    return cosine_similarity(fused_vec, restaurant_vec)


def compute_price_match(user_price_pref: list[str] | str | None, restaurant_price: str | None) -> float:
    """Score how well the restaurant price matches the user's preference."""
    if isinstance(user_price_pref, list):
        user_price_pref = user_price_pref[0] if user_price_pref else None

    if not user_price_pref:
        return 0.5
    if not restaurant_price:
        return 0.5

    user_level = _normalize_price_level(user_price_pref)
    restaurant_level = _normalize_price_level(restaurant_price)

    if user_level <= 0.0 or restaurant_level <= 0.0:
        return 0.5

    difference = abs(user_level - restaurant_level)
    if difference == 0:
        return 1.0
    if difference == 1:
        return 0.75
    if difference == 2:
        return 0.5
    if difference == 3:
        return 0.25
    return 0.0


def compute_rating_score(rating: float | None) -> float:
    """Normalize a 5-star rating to the range ``[0, 1]``."""
    return clamp(to_float(rating, 0.0) / 5.0)


def compute_popularity_score(review_count: int | None) -> float:
    """Transform review counts into a bounded popularity score."""
    review_value = max(0.0, to_float(review_count, 0.0))
    return clamp(safe_log1p(review_value) / safe_log1p(5000.0))


def compute_distance_penalty(distance_km: float | None, max_distance_km: float = 10.0) -> float:
    """Return a proximity score where closer restaurants score better."""
    return _distance_score(distance_km, max_distance_km=max_distance_km)


def compute_soft_preference_boost(
    restaurant: dict[str, Any],
    soft_preferences: dict[str, Any] | None = None,
) -> float:
    """Compute the aggregate soft boost from already-parsed filter signals."""
    if not soft_preferences:
        return 0.0

    dietary = compute_dietary_preference_boost(restaurant, soft_preferences)
    location = compute_location_preference_boost(restaurant, soft_preferences)
    cuisine = compute_cuisine_preference_boost(restaurant, soft_preferences)
    price = 0.05 * compute_price_match(soft_preferences.get("price"), restaurant.get("price"))
    vibe = compute_vibe_preference_boost(restaurant, soft_preferences)
    meal_type = compute_meal_type_boost(restaurant, soft_preferences)

    return min(0.50, dietary + location + cuisine + price + vibe + meal_type)


def _merge_weights(weights: dict[str, float] | None) -> dict[str, float]:
    merged_weights = dict(DEFAULT_RANKING_WEIGHTS)
    if weights:
        for key, value in weights.items():
            merged_weights[key] = to_float(value, merged_weights.get(key, 0.0))

    total = sum(max(0.0, weight) for weight in merged_weights.values())
    if total <= 0.0:
        return dict(DEFAULT_RANKING_WEIGHTS)

    return {key: max(0.0, weight) / total for key, weight in merged_weights.items()}


def compute_final_score(
    semantic_score: float,
    rating_score: float,
    popularity_score: float,
    price_match_score: float,
    distance_score: float,
    weights: dict[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    """Combine all score components into a final ranking score."""
    normalized_weights = _merge_weights(weights)
    breakdown = {
        "semantic": clamp(semantic_score, -1.0, 1.0),
        "rating": clamp(rating_score),
        "popularity": clamp(popularity_score),
        "price_match": clamp(price_match_score),
        "distance": clamp(distance_score),
    }

    final_score = 0.0
    for key, component_score in breakdown.items():
        final_score += normalized_weights.get(key, 0.0) * component_score

    return clamp(final_score), breakdown


def rank_candidates(
    candidates: list[tuple[dict[str, Any], float]],
    active_filters: dict[str, Any] | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Compute final ranking scores using semantic relevance, hard signals, and soft boosts."""
    filters = active_filters or {}
    user_price_pref = filters.get("price")

    ranked_results: list[dict[str, Any]] = []
    for restaurant, similarity_score in candidates:
        if not isinstance(restaurant, dict):
            continue

        rating_score = compute_rating_score(restaurant.get("rating"))
        popularity_score = compute_popularity_score(restaurant.get("review_count"))
        dietary_boost = compute_dietary_preference_boost(restaurant, filters)
        location_boost = compute_location_preference_boost(restaurant, filters)
        cuisine_boost = compute_cuisine_preference_boost(restaurant, filters)
        price_match = compute_price_match(user_price_pref, restaurant.get("price"))
        price_boost = price_match if user_price_pref else 0.0
        vibe_boost = compute_vibe_preference_boost(restaurant, filters)
        meal_type_boost = compute_meal_type_boost(restaurant, filters)
        distance_component = compute_distance_penalty(restaurant.get("distance_km"))

        final_score, breakdown = compute_final_score(
            semantic_score=similarity_score,
            rating_score=rating_score,
            popularity_score=popularity_score,
            price_match_score=price_match,
            distance_score=distance_component,
        )
        weighted_boost = (
            (BOOST_WEIGHTS["dietary"] * dietary_boost)
            + (BOOST_WEIGHTS["location"] * location_boost)
            + (BOOST_WEIGHTS["cuisine"] * cuisine_boost)
            + (BOOST_WEIGHTS["price"] * price_boost)
            + (BOOST_WEIGHTS["vibe"] * vibe_boost)
            + (BOOST_WEIGHTS["meal_type"] * meal_type_boost)
        )
        final_score = clamp(final_score + weighted_boost)
        
                
        # Dietary + Location Distance Guardrail
        has_location_intent = bool(
            filters.get("location")
            or filters.get("origin_lat") is not None
            or filters.get("origin_lon") is not None
            or filters.get("nearby")
        )

        breakdown["dietary_match"] = dietary_boost
        breakdown["location_match"] = location_boost
        breakdown["cuisine_match"] = cuisine_boost
        breakdown["price_filter_match"] = price_boost
        breakdown["vibe_match"] = vibe_boost
        breakdown["meal_type_match"] = meal_type_boost
        breakdown["total_filter_boost"] = weighted_boost

        result = dict(restaurant)
        result["semantic_score"] = similarity_score
        result["final_score"] = final_score
        result["score_breakdown"] = breakdown
        result["soft_preference_boost"] = weighted_boost
        result["dietary_match_boost"] = dietary_boost
        ranked_results.append(result)

    ranked_results.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
    if top_k is not None:
        return ranked_results[:top_k]
    return ranked_results
