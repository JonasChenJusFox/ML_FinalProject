"""
integration/api.py
Owner: Nick

Responsibilities:
- Glue layer connecting data, embeddings, and ranking modules
- Single entry point for the frontend to call
- Orchestrates the full search pipeline:
    1. Embed the query
    2. Retrieve semantic candidates
    3. Apply structured filters
    4. Rank and personalize results
    5. Return final result list
"""

from __future__ import annotations

import math
from pathlib import Path
import re

from config.settings import EMBEDDING_MODEL
from data.pipeline import load_restaurants, load_user_interactions
from embeddings.cluster_retrieval import load_centroids, load_restaurant_index, retrieve_candidates
from embeddings.vectorizer import (
    build_restaurant_index,
    embed_query,
    embed_user,
    retrieve_top_k,
)
from integration.location_context import (
    annotate_area_distance,
    extract_search_area,
    filter_restaurants_by_area,
    is_generic_area_query,
)
from integration.borough_utils import canonicalize_borough, infer_borough, matches_location_filter
from integration.price_utils import canonicalize_price_label
from integration.wrapped_repo import build_wrapped_stats
from recommendation.algorithm import recommend_top_restaurants
from recommendation.ranker import apply_filters, fuse_vectors, rank_candidates, rank_candidates_from_fused_vector
from integration.user_repo import get_user_profile, update_latest_embedding

# ---------------------------------------------------------------------------
# Module-level cache (populated on first call)
# ---------------------------------------------------------------------------
_restaurant_index = None
_restaurants = None
_restaurant_lookup = None
_cluster_restaurant_index = None
_cluster_centroids = None
NYU_LAT = 40.7295
NYU_LON = -73.9965
REPO_ROOT = Path(__file__).resolve().parent.parent
RESTAURANT_EMBEDDINGS_PATH = REPO_ROOT / "data" / "restaurant_embeddings.json"
CLUSTER_CENTROIDS_PATH = REPO_ROOT / "data" / "cluster_centroids.json"
PERSONALIZATION_ALPHA = 0.3
PRICE_QUERY_PATTERNS: dict[str, tuple[str, ...]] = {
    "cheap": (
        "cheap",
        "affordable",
        "budget",
        "budget-friendly",
        "budget friendly",
        "inexpensive",
        "low-cost",
        "low cost",
        "cheap eats",
    ),
    "moderate": (
        "moderate",
        "mid-range",
        "mid range",
        "reasonably priced",
        "reasonable price",
    ),
    "expensive": (
        "expensive",
        "pricey",
        "upscale",
    ),
    "luxury": (
        "luxury",
        "fine dining",
        "high-end",
        "high end",
        "premium",
    ),
}
PRICE_SYMBOL_PATTERNS: dict[str, tuple[str, ...]] = {
    "cheap": ("$",),
    "moderate": ("$$",),
    "expensive": ("$$$",),
    "luxury": ("$$$$",),
}
BOROUGH_QUERY_PATTERNS: dict[str, tuple[str, ...]] = {
    "Manhattan": ("manhattan",),
    "Brooklyn": ("brooklyn",),
    "Queens": ("queens", "queens ny"),
    "Bronx": ("bronx", "the bronx"),
    "Staten Island": ("staten island",),
}
RATING_QUERY_PATTERNS: dict[float, tuple[str, ...]] = {
    4.5: ("highly rated",),
    4.7: ("top rated", "best rated"),
}
NEAR_ME_PATTERNS: tuple[str, ...] = (
    "near me",
    "around me",
    "close to me",
    "near my location",
    "my location",
)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _extract_coordinates(restaurant: dict) -> tuple[float | None, float | None]:
    if not isinstance(restaurant, dict):
        return None, None

    coordinates = restaurant.get("coordinates", {})

    latitude = _optional_float(restaurant.get("latitude"))
    longitude = _optional_float(restaurant.get("longitude"))

    if isinstance(coordinates, dict):
        if latitude is None:
            latitude = _optional_float(coordinates.get("latitude"))
        if longitude is None:
            longitude = _optional_float(coordinates.get("longitude"))

    return latitude, longitude


def _resolve_origin(origin_lat: float | None, origin_lon: float | None) -> tuple[float, float]:
    latitude = _optional_float(origin_lat)
    longitude = _optional_float(origin_lon)

    if latitude is None or longitude is None:
        return NYU_LAT, NYU_LON

    return latitude, longitude


def _with_distance_km(
    restaurants: list[dict],
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> list[dict]:
    resolved_origin_lat, resolved_origin_lon = _resolve_origin(origin_lat, origin_lon)
    enriched: list[dict] = []
    for restaurant in restaurants:
        item = dict(restaurant)
        lat = item.get("_resolved_latitude")
        lon = item.get("_resolved_longitude")
        if lat is None or lon is None:
            lat, lon = _extract_coordinates(item)
        item["latitude"] = lat
        item["longitude"] = lon
        item["borough"] = item.get("_resolved_borough") or infer_borough(item)
        if lat is not None and lon is not None:
            item["distance_km"] = haversine_km(resolved_origin_lat, resolved_origin_lon, lat, lon)
        else:
            item["distance_km"] = None
        enriched.append(item)
    return enriched


def _rank_by_location_and_rating(
    restaurants: list[dict],
    filters: dict,
    top_k: int,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> list[dict]:
    ranked = _with_distance_km(restaurants, origin_lat=origin_lat, origin_lon=origin_lon)
    ranked = apply_filters(ranked, filters)
    ranked = _apply_borough_filter(ranked, filters.get("borough"))

    ranked.sort(
        key=lambda item: (
            _safe_float(item.get("distance_km"), 1e9),
            -_safe_float(item.get("rating"), 0.0),
        )
    )

    for item in ranked:
        rating = _safe_float(item.get("rating"), 0.0) / 5.0
        distance = _safe_float(item.get("distance_km"), 1e9)
        item["semantic_score"] = 0.0
        distance_score = max(0.0, 1.0 - min(distance / 10.0, 1.0))
        item["final_score"] = (distance_score * 0.7) + (rating * 0.3)

    return ranked[:top_k]


def _rank_by_area_and_rating(
    restaurants: list[dict],
    filters: dict,
    top_k: int,
    search_area: dict,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> list[dict]:
    ranked = _with_distance_km(restaurants, origin_lat=origin_lat, origin_lon=origin_lon)
    ranked = apply_filters(ranked, filters)
    ranked = _apply_borough_filter(ranked, filters.get("borough"))
    ranked = filter_restaurants_by_area(ranked, search_area)
    ranked = annotate_area_distance(ranked, search_area)

    ranked.sort(
        key=lambda item: (
            _safe_float(item.get("query_area_distance_km"), 1e9),
            -_safe_float(item.get("rating"), 0.0),
            _safe_float(item.get("distance_km"), 1e9),
        )
    )

    area_radius_km = max(_safe_float(search_area.get("radius_km"), 1.0), 0.1)
    for item in ranked:
        area_distance = _safe_float(item.get("query_area_distance_km"), area_radius_km)
        rating = _safe_float(item.get("rating"), 0.0) / 5.0
        current_distance = _safe_float(item.get("distance_km"), 10.0)
        area_score = max(0.0, 1.0 - min(area_distance / area_radius_km, 1.0))
        current_distance_score = max(0.0, 1.0 - min(current_distance / 10.0, 1.0))
        item["semantic_score"] = 0.0
        item["final_score"] = (area_score * 0.6) + (rating * 0.3) + (current_distance_score * 0.1)

    return ranked[:top_k]


def _get_restaurants() -> list[dict]:
    """Lazy-load and cache restaurant records."""
    global _restaurants, _restaurant_lookup
    if _restaurants is None:
        _restaurants = load_restaurants()
        _restaurant_lookup = {}
        for restaurant in _restaurants:
            if not isinstance(restaurant, dict):
                continue
            lat, lon = _extract_coordinates(restaurant)
            restaurant["_resolved_latitude"] = lat
            restaurant["_resolved_longitude"] = lon
            restaurant["_resolved_borough"] = infer_borough(restaurant)
            business_id = str(restaurant.get("business_id", "")).strip()
            if business_id:
                _restaurant_lookup[business_id] = restaurant
    return _restaurants


def _adapt_filters(filters: dict | None) -> dict:
    """Normalize frontend/backend filter payloads to ranker filter schema."""
    filters = filters or {}

    cuisines = (
        filters.get("cuisines")
        or filters.get("categories")
        or filters.get("discover_categories")
        or []
    )

    prices = (
        filters.get("price")
        or filters.get("prices")
        or filters.get("discover_prices")
        or []
    )

    min_rating = filters.get("min_rating")
    if min_rating is None:
        min_rating = filters.get("discover_min_rating", 0.0)

    max_distance_km = filters.get("max_distance_km")
    if max_distance_km is None and filters.get("discover_radius_minutes") is not None:
        try:
            max_distance_km = float(filters.get("discover_radius_minutes", 0)) * 0.33
        except (TypeError, ValueError):
            max_distance_km = None

    borough = filters.get("borough")
    if borough is None:
        borough = filters.get("discover_borough", "All")
    if borough not in {None, "", "All"}:
        borough = canonicalize_borough(borough)

    return {
        "cuisines": list(cuisines) if isinstance(cuisines, list) else [],
        "price": list(prices) if isinstance(prices, list) else [],
        "min_rating": min_rating,
        "max_distance_km": max_distance_km,
        "borough": borough,
    }


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _extract_query_price_filters(query: str) -> tuple[str, list[str]]:
    normalized_query = _normalize_whitespace(query).lower()
    if not normalized_query:
        return "", []

    matched_prices: list[str] = []
    working_query = normalized_query

    symbol_variants: list[tuple[str, str]] = []
    for price_label, variants in PRICE_SYMBOL_PATTERNS.items():
        for symbol in variants:
            symbol_variants.append((symbol, price_label))

    for symbol, price_label in sorted(symbol_variants, key=lambda item: len(item[0]), reverse=True):
        if symbol and symbol in working_query:
            matched_prices.append(price_label)
            working_query = working_query.replace(symbol, " ")

    for price_label, variants in PRICE_QUERY_PATTERNS.items():
        for variant in sorted(variants, key=len, reverse=True):
            pattern = rf"\b{re.escape(variant)}\b"
            if re.search(pattern, working_query):
                matched_prices.append(price_label)
                working_query = re.sub(pattern, " ", working_query)

    cleaned_query = _normalize_whitespace(working_query)
    deduped_prices = list(dict.fromkeys(matched_prices))
    return cleaned_query, deduped_prices


def _extract_query_borough_filter(query: str) -> tuple[str, str | None]:
    normalized_query = _normalize_whitespace(query).lower()
    if not normalized_query:
        return "", None

    working_query = normalized_query
    matched_borough = None

    for borough, variants in BOROUGH_QUERY_PATTERNS.items():
        for variant in sorted(variants, key=len, reverse=True):
            pattern = rf"\b{re.escape(variant)}\b"
            if re.search(pattern, working_query):
                matched_borough = borough
                working_query = re.sub(pattern, " ", working_query)
                break
        if matched_borough:
            break

    return _normalize_whitespace(working_query), matched_borough


def _strip_near_me_phrases(query: str) -> str:
    working_query = _normalize_whitespace(query).lower()
    if not working_query:
        return ""

    for phrase in sorted(NEAR_ME_PATTERNS, key=len, reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])"
        working_query = re.sub(pattern, " ", working_query)

    return _normalize_whitespace(working_query)


def _merge_query_inferred_filters(
    adapted_filters: dict,
    inferred_prices: list[str],
    inferred_borough: str | None,
    inferred_min_rating: float | None = None,
) -> dict:
    merged_filters = dict(adapted_filters)
    explicit_prices = merged_filters.get("price", [])
    if explicit_prices:
        merged_filters["price"] = [
            canonicalize_price_label(price) or str(price).strip().lower()
            for price in explicit_prices
            if str(price).strip()
        ]
    elif inferred_prices:
        merged_filters["price"] = inferred_prices

    explicit_borough = str(merged_filters.get("borough") or "All").strip()
    if (not explicit_borough or explicit_borough == "All") and inferred_borough:
        merged_filters["borough"] = inferred_borough

    if inferred_min_rating is not None:
        explicit_min_rating = _safe_float(merged_filters.get("min_rating"), 0.0)
        merged_filters["min_rating"] = max(explicit_min_rating, inferred_min_rating)

    return merged_filters


def _extract_query_rating_filter(query: str) -> tuple[str, float | None]:
    normalized_query = _normalize_whitespace(query).lower()
    if not normalized_query:
        return "", None

    working_query = normalized_query
    matched_rating = None

    numeric_match = re.search(r"\b([0-5](?:\.\d)?)\s*[- ]?star(?:s)?\b", working_query)
    if numeric_match:
        matched_rating = max(0.0, min(5.0, _safe_float(numeric_match.group(1), 0.0)))
        working_query = re.sub(r"\b[0-5](?:\.\d)?\s*[- ]?star(?:s)?\b", " ", working_query)

    for rating_value, variants in RATING_QUERY_PATTERNS.items():
        for variant in sorted(variants, key=len, reverse=True):
            pattern = rf"\b{re.escape(variant)}\b"
            if re.search(pattern, working_query):
                matched_rating = max(matched_rating or 0.0, rating_value)
                working_query = re.sub(pattern, " ", working_query)

    cleaned_query = _normalize_whitespace(working_query)
    return cleaned_query, matched_rating


def _has_structured_filters(filters: dict | None) -> bool:
    normalized = filters or {}
    if normalized.get("cuisines"):
        return True
    if normalized.get("price"):
        return True
    if normalized.get("max_distance_km") is not None:
        return True
    if _safe_float(normalized.get("min_rating"), 0.0) > 0.0:
        return True

    borough_value = str(normalized.get("borough") or "").strip()
    return bool(borough_value and borough_value != "All")


def _apply_borough_filter(restaurants: list[dict], borough: str | None) -> list[dict]:
    normalized_borough = canonicalize_borough(borough)
    raw_selection = str(borough or "").strip()
    if (not normalized_borough and not raw_selection) or raw_selection == "All" or normalized_borough == "All":
        return restaurants
    return [
        item
        for item in restaurants
        if matches_location_filter(item, raw_selection or normalized_borough)
    ]


def _build_user_embedding_if_available(user_id: str) -> list[float] | None:
    """Build user embedding from profile, cached vector, or interaction history."""
    if not user_id or user_id == "anonymous":
        return None

    profile = get_user_profile(user_id)
    if profile:
        latest_embedding = profile.get("latest_embedding")
        if isinstance(latest_embedding, dict):
            vector = latest_embedding.get("vector")
            model_name = str(latest_embedding.get("model_name", "")).strip()
            if (
                isinstance(vector, list)
                and vector
                and model_name == EMBEDDING_MODEL
            ):
                return vector

        user_document = str(profile.get("profile_text", "")).strip()
        if user_document:
            try:
                vector = embed_user(user_document)
                if isinstance(vector, list) and vector:
                    update_latest_embedding(user_id, vector)
                    return vector
            except Exception:
                pass

    interactions = load_user_interactions(user_id)
    if not interactions:
        return None

    interaction_terms: list[str] = []
    for record in interactions:
        if not isinstance(record, dict):
            continue

        interaction_name = str(
            record.get("interaction_type", record.get("action", ""))
        ).strip()
        if interaction_name:
            interaction_terms.append(interaction_name)

        inferred_tags = record.get("inferred_food_tags", record.get("tags", []))
        if isinstance(inferred_tags, list):
            interaction_terms.extend(
                str(tag).strip()
                for tag in inferred_tags
                if str(tag).strip()
            )

    if not interaction_terms:
        return None

    try:
        vector = embed_user(" ".join(interaction_terms))
        return vector if isinstance(vector, list) and vector else None
    except Exception:
        return None


def _adapt_questionnaire_answers_for_recommendation(raw_answers: dict | None) -> dict:
    answers = raw_answers if isinstance(raw_answers, dict) else {}
    travel_willingness = str(answers.get("travel_willingness", "")).strip()
    legacy_location = {
        "Walking distance (< 10 min / ~0.5 mi)": "near home",
        "Short commute (10–20 min / ~1 mi)": "near school/work",
        "Across the neighborhood (20–35 min)": "near school/work",
        "Anywhere in the city": "will travel for food",
    }.get(travel_willingness, "")

    return {
        "favorite_cuisines": list(answers.get("top_cuisines", [])),
        "cravings": list(answers.get("craving_preferences", [])),
        "price_range": canonicalize_price_label(answers.get("price_comfort_level", "moderate")) or "moderate",
        "place_types": list(answers.get("vibes_dining_style", [])),
        "dietary": list(answers.get("dietary_restrictions", [])),
        "usual_location": legacy_location,
        "meals": list(answers.get("typical_meals", [])),
        "decision_style": list(answers.get("decision_criteria", [])),
        "novelty_preference": str(answers.get("novelty_preference", "mix of both")).strip() or "mix of both",
        "favorite_dishes": list(answers.get("favorite_dishes", [])),
        "frequent_restaurants": list(answers.get("frequent_restaurants", [])),
        "dream_restaurants": list(answers.get("aspirational_restaurants", [])),
    }


def _get_index():
    """Lazy-load and cache the restaurant embedding index."""
    global _restaurant_index, _restaurants
    if _restaurant_index is None:
        _restaurants = _get_restaurants()
        _restaurant_index = build_restaurant_index(_restaurants)
    return _restaurant_index, _restaurants


def _get_cluster_assets() -> tuple[list[dict] | None, list[dict] | None]:
    """Load precomputed cluster retrieval assets if available."""
    global _cluster_restaurant_index, _cluster_centroids

    if _cluster_restaurant_index is not None and _cluster_centroids is not None:
        return _cluster_restaurant_index, _cluster_centroids

    if not RESTAURANT_EMBEDDINGS_PATH.exists() or not CLUSTER_CENTROIDS_PATH.exists():
        return None, None

    try:
        _cluster_restaurant_index = load_restaurant_index(str(RESTAURANT_EMBEDDINGS_PATH))
        _cluster_centroids = load_centroids(str(CLUSTER_CENTROIDS_PATH))
        return _cluster_restaurant_index, _cluster_centroids
    except Exception:
        _cluster_restaurant_index = None
        _cluster_centroids = None
        return None, None


def _retrieve_candidates_cluster_first(
    fused_vector: list[float],
    k: int,
) -> list[tuple[dict, float]]:
    """Retrieve candidates using cluster-first retrieval, fallback to global top-k."""
    cluster_index, cluster_centroids = _get_cluster_assets()
    restaurants = _get_restaurants()

    if cluster_index is not None and cluster_centroids is not None:
        try:
            business_id_to_restaurant = {
                str(item.get("business_id", "")): item
                for item in restaurants
                if isinstance(item, dict)
            }

            cluster_hits = retrieve_candidates(
                query_vector=fused_vector,
                index=cluster_index,
                centroids=cluster_centroids,
                k=k,
            )

            candidates: list[tuple[dict, float]] = []
            for business_id, score, _cluster_id in cluster_hits:
                restaurant = business_id_to_restaurant.get(str(business_id))
                if restaurant is None:
                    continue
                candidates.append((restaurant, score))

            if candidates:
                return candidates
        except Exception:
            pass

    index, _ = _get_index()
    return retrieve_top_k(fused_vector, index, k=k)


def _merge_retrieval_candidates(
    query_candidates: list[tuple[dict, float]],
    personalized_candidates: list[tuple[dict, float]],
) -> list[tuple[dict, float]]:
    merged: dict[str, dict] = {}

    for restaurant, score in query_candidates:
        if not isinstance(restaurant, dict):
            continue
        business_id = str(restaurant.get("business_id", "")).strip()
        if not business_id:
            continue
        slot = merged.setdefault(
            business_id,
            {"restaurant": restaurant, "query_score": None, "personalized_score": None},
        )
        slot["restaurant"] = restaurant
        slot["query_score"] = _safe_float(score, 0.0)

    for restaurant, score in personalized_candidates:
        if not isinstance(restaurant, dict):
            continue
        business_id = str(restaurant.get("business_id", "")).strip()
        if not business_id:
            continue
        slot = merged.setdefault(
            business_id,
            {"restaurant": restaurant, "query_score": None, "personalized_score": None},
        )
        slot["restaurant"] = restaurant
        slot["personalized_score"] = _safe_float(score, 0.0)

    blended: list[tuple[dict, float]] = []
    for payload in merged.values():
        query_score = payload.get("query_score")
        personalized_score = payload.get("personalized_score")

        if query_score is not None and personalized_score is not None:
            combined_score = (query_score * 0.75) + (personalized_score * 0.25)
        elif query_score is not None:
            combined_score = query_score
        else:
            combined_score = _safe_float(personalized_score, 0.0) * 0.85

        blended.append((payload["restaurant"], combined_score))

    blended.sort(key=lambda item: _safe_float(item[1], 0.0), reverse=True)
    return blended


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_restaurants(
    query: str,
    filters: dict | None,
    user_id: str = "anonymous",
    top_k: int = 20,
    user_vector_only: bool = False,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> list[dict]:
    """
    Full search pipeline: semantic retrieval → filtering → personalized ranking.

    Args:
        query:   Natural language query from the user.
        filters: Structured filter dict from the UI sidebar.
        user_id: Current user ID (for personalization). Defaults to anonymous.
        top_k:   Max number of results to return.

    Returns:
        Ordered list of restaurant dicts (best match first).
    """
    requested_top_k = max(1, int(top_k))

    raw_query_text = (query or "").strip()
    price_cleaned_query, inferred_price_filters = _extract_query_price_filters(raw_query_text)
    rating_cleaned_query, inferred_min_rating = _extract_query_rating_filter(price_cleaned_query)
    borough_cleaned_query, inferred_borough = _extract_query_borough_filter(rating_cleaned_query)
    near_me_cleaned_query = _strip_near_me_phrases(borough_cleaned_query)
    query_text, search_area = extract_search_area(near_me_cleaned_query)

    # Step 1: load existing user embedding if available
    user_vector = _build_user_embedding_if_available(user_id)
    adapted_filters = _merge_query_inferred_filters(
        _adapt_filters(filters),
        inferred_price_filters,
        inferred_borough,
        inferred_min_rating,
    )

    structured_query_only = bool(raw_query_text) and (
        (not query_text and (inferred_price_filters or inferred_borough))
        or (search_area is not None and is_generic_area_query(query_text))
    )

    # Purely structured price / area queries should skip embedding retrieval entirely.
    if structured_query_only:
        fallback_restaurants = _get_restaurants()
        if search_area is not None:
            return _rank_by_area_and_rating(
                restaurants=fallback_restaurants,
                filters=adapted_filters,
                top_k=requested_top_k,
                search_area=search_area,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )
        return _rank_by_location_and_rating(
            restaurants=fallback_restaurants,
            filters=adapted_filters,
            top_k=requested_top_k,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )

    has_structured_filters = _has_structured_filters(adapted_filters)

    # Mode split:
    # - recommendation mode: empty query and no structured filters -> user vector only
    # - filtered browse mode: empty query with filters -> keep full recall, personalize ranking only
    # - search mode: non-empty query -> semantic retrieval with personalization-aware reranking
    use_recommendation_mode = user_vector_only or (not query_text and not has_structured_filters)

    if use_recommendation_mode:
        if user_vector is None:
            fallback_restaurants = _get_restaurants()
            return _rank_by_location_and_rating(
                restaurants=fallback_restaurants,
                filters=adapted_filters,
                top_k=requested_top_k,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

        query_vector = [0.0] * len(user_vector)
        fused_vector = fuse_vectors(query_vector, user_vector, alpha=1.0)
        candidates = _retrieve_candidates_cluster_first(fused_vector, k=requested_top_k * 3)
    elif not query_text:
        filtered_restaurants = _with_distance_km(
            _get_restaurants(),
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )
        if search_area is not None:
            filtered_restaurants = filter_restaurants_by_area(filtered_restaurants, search_area)
        filtered_restaurants = apply_filters(filtered_restaurants, adapted_filters)
        filtered_restaurants = _apply_borough_filter(filtered_restaurants, adapted_filters.get("borough"))

        if search_area is not None:
            filtered_restaurants = annotate_area_distance(filtered_restaurants, search_area)

        if user_vector is None:
            return _rank_by_location_and_rating(
                restaurants=_get_restaurants(),
                filters=adapted_filters,
                top_k=requested_top_k,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

        ranked = rank_candidates_from_fused_vector(user_vector, filtered_restaurants)
        return ranked[:requested_top_k]
    else:
        query_vector = embed_query(query_text)
        if user_vector is None:
            candidates = _retrieve_candidates_cluster_first(query_vector, k=requested_top_k * 3)
        else:
            fused_vector = fuse_vectors(query_vector, user_vector, alpha=PERSONALIZATION_ALPHA)
            retrieval_k = max(requested_top_k * 3, 120)
            query_candidates = _retrieve_candidates_cluster_first(query_vector, k=retrieval_k)
            personalized_candidates = _retrieve_candidates_cluster_first(fused_vector, k=retrieval_k)
            candidates = _merge_retrieval_candidates(query_candidates, personalized_candidates)

    # Step 3: retrieve semantic candidates (cluster-first, then within-cluster search)

    # Step 4: apply structured filters
    candidate_restaurants = [r for r, _ in candidates]
    #add distance maximum before filtering
    candidate_restaurants = _with_distance_km(
        candidate_restaurants,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )
    if search_area is not None:
        candidate_restaurants = filter_restaurants_by_area(candidate_restaurants, search_area)
    filtered = apply_filters(candidate_restaurants, adapted_filters)
    filtered = _apply_borough_filter(filtered, adapted_filters.get("borough"))

    if search_area is not None:
        filtered = annotate_area_distance(filtered, search_area)

    if search_area is not None and not filtered:
        return _rank_by_area_and_rating(
            restaurants=_get_restaurants(),
            filters=adapted_filters,
            top_k=requested_top_k,
            search_area=search_area,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )

    # Step 5: Rebuild (restaurant, score) tuples after filtering
    score_map = {
        str(restaurant.get("business_id", "")): score
        for restaurant, score in candidates
        if isinstance(restaurant, dict)
    }
    
    filtered_with_scores = [
        (restaurant, score_map.get(str(restaurant.get("business_id", "")), 0.0))
        for restaurant in filtered
    ]

    # Step 6: rank candidates
    user_history = load_user_interactions(user_id) if user_id != "anonymous" else []
    ranked = rank_candidates(filtered_with_scores, user_history)

    # Step 7: return top-k
    return ranked[:requested_top_k]


def get_recommendations_for_user(
    user_id: str,
    top_k: int = 10,
    candidate_top_k: int = 50,
    filters: dict | None = None,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
) -> list[dict]:
    """Return recommendation-page results through a single backend facade."""
    if not user_id or user_id == "anonymous":
        return []

    profile = get_user_profile(user_id) or {}
    questionnaire_answers = _adapt_questionnaire_answers_for_recommendation(
        profile.get("raw_answers"),
    )

    all_restaurants = _with_distance_km(
        _get_restaurants(),
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )
    wrapped_stats = build_wrapped_stats(user_id, all_restaurants)

    if not any(questionnaire_answers.values()) and not (
        wrapped_stats.get("saved_count", 0) or wrapped_stats.get("reviewed_count", 0)
    ):
        return []

    query_parts = (
        questionnaire_answers.get("favorite_cuisines", [])
        + questionnaire_answers.get("cravings", [])
        + questionnaire_answers.get("place_types", [])
        + questionnaire_answers.get("favorite_dishes", [])
    )
    query = " ".join(query_parts) if query_parts else "restaurant"

    candidates = search_restaurants(
        query=query,
        filters=filters,
        user_id=user_id,
        top_k=max(int(candidate_top_k), int(top_k)),
        user_vector_only=False,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )

    recommendation_source = candidates if candidates else all_restaurants
    return recommend_top_restaurants(
        restaurants=recommendation_source,
        questionnaire_answers=questionnaire_answers,
        wrapped_stats=wrapped_stats,
        top_k=top_k,
    )


def get_all_restaurants() -> list[dict]:
    """Return the full cached restaurant list."""
    return list(_get_restaurants())


def get_restaurants_by_ids(business_ids: list[str]) -> list[dict]:
    """Return restaurants for the requested business ids, preserving order."""
    _get_restaurants()
    results: list[dict] = []
    seen: set[str] = set()

    for business_id in business_ids:
        normalized_id = str(business_id or "").strip()
        if not normalized_id or normalized_id in seen:
            continue
        seen.add(normalized_id)
        restaurant = (_restaurant_lookup or {}).get(normalized_id)
        if restaurant:
            results.append(dict(restaurant))

    return results


def debug_compare_queries(
    user_id: str,
    query_a: str,
    query_b: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> dict:
    """Print and return top results for two queries under the same user."""
    results_a = search_restaurants(
        query=query_a,
        filters=filters,
        user_id=user_id,
        top_k=top_k,
        user_vector_only=False,
    )
    results_b = search_restaurants(
        query=query_b,
        filters=filters,
        user_id=user_id,
        top_k=top_k,
        user_vector_only=False,
    )

    ids_a = [str(item.get("business_id", "")) for item in results_a]
    ids_b = [str(item.get("business_id", "")) for item in results_b]
    names_a = [str(item.get("name", "")) for item in results_a]
    names_b = [str(item.get("name", "")) for item in results_b]
    overlap = sorted(set(ids_a) & set(ids_b))

    print(f"[debug_compare_queries] user={user_id}")
    print(f"query_a={query_a!r} -> {names_a}")
    print(f"query_b={query_b!r} -> {names_b}")
    print(f"overlap_count={len(overlap)} overlap_ids={overlap}")

    return {
        "user_id": user_id,
        "query_a": query_a,
        "query_b": query_b,
        "top_k": top_k,
        "ids_a": ids_a,
        "ids_b": ids_b,
        "names_a": names_a,
        "names_b": names_b,
        "overlap_ids": overlap,
        "overlap_count": len(overlap),
    }


def debug_compare_users_same_query(
    user_a: str,
    user_b: str,
    query: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> dict:
    """Print and return top results for the same query under two different users."""
    results_a = search_restaurants(
        query=query,
        filters=filters,
        user_id=user_a,
        top_k=top_k,
        user_vector_only=False,
    )
    results_b = search_restaurants(
        query=query,
        filters=filters,
        user_id=user_b,
        top_k=top_k,
        user_vector_only=False,
    )

    ids_a = [str(item.get("business_id", "")) for item in results_a]
    ids_b = [str(item.get("business_id", "")) for item in results_b]
    names_a = [str(item.get("name", "")) for item in results_a]
    names_b = [str(item.get("name", "")) for item in results_b]
    overlap = sorted(set(ids_a) & set(ids_b))

    print(f"[debug_compare_users_same_query] query={query!r}")
    print(f"user_a={user_a} -> {names_a}")
    print(f"user_b={user_b} -> {names_b}")
    print(f"overlap_count={len(overlap)} overlap_ids={overlap}")

    return {
        "query": query,
        "user_a": user_a,
        "user_b": user_b,
        "top_k": top_k,
        "ids_a": ids_a,
        "ids_b": ids_b,
        "names_a": names_a,
        "names_b": names_b,
        "overlap_ids": overlap,
        "overlap_count": len(overlap),
    }


def get_restaurant_by_id(business_id: str) -> dict | None:
    """
    Fetch a single restaurant by its Yelp business ID.

    Args:
        business_id: Yelp business ID string.

    Returns:
        Restaurant dict, or None if not found.
    """
    _, restaurants = _get_index()
    for r in restaurants:
        if r.get("business_id") == business_id:
            return r
    return None
