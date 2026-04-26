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

from data.pipeline import load_restaurants, load_user_interactions
from embeddings.cluster_retrieval import load_centroids, load_restaurant_index, retrieve_candidates
from embeddings.query_parser import parse_query, minimal_clean_query
from embeddings.location_lookup import resolve_location_coordinate
from embeddings.vectorizer import (
    build_restaurant_index,
    embed_query,
    embed_user,
    retrieve_top_k,
)
from recommendation.ranker import apply_filters, fuse_vectors, rank_candidates
from integration.user_repo import get_user_profile, update_latest_embedding

# ---------------------------------------------------------------------------
# Module-level cache (populated on first call)
# ---------------------------------------------------------------------------
_restaurant_index = None
_restaurants = None
_cluster_restaurant_index = None
_cluster_centroids = None
NYU_LAT = 40.7295
NYU_LON = -73.9965
REPO_ROOT = Path(__file__).resolve().parent.parent
RESTAURANT_EMBEDDINGS_PATH = REPO_ROOT / "data" / "restaurant_embeddings.json"
CLUSTER_CENTROIDS_PATH = REPO_ROOT / "data" / "cluster_centroids.json"
PERSONALIZATION_ALPHA = 0.3
PROFILE_VECTOR_WEIGHT = 0.7
INTERACTION_VECTOR_WEIGHT = 0.3
SOFT_FILTER_MIN_RESULTS = 10
HARD_FILTER_FALLBACK_MIN_RESULTS = 5
DEFAULT_NEARBY_DISTANCE_KM = 5.0
WALKING_SPEED_KMPH = 5.0
INTERACTION_WEIGHTS = {
    "save": 1.0,
    "like": 1.5,
    ("review", "love"): 2.0,
    ("review", "neutral"): 0.5,
    ("review", "hate"): 0.0,
}


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def manhattan_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate NYC walking distance using Manhattan-style blocks.

    Formula:
      lat_distance_km = abs(lat1 - lat2) * 111
      lon_distance_km = abs(lon1 - lon2) * 85
      distance_km = lat_distance_km + lon_distance_km
    """
    lat_distance_km = abs(lat1 - lat2) * 111.0
    lon_distance_km = abs(lon1 - lon2) * 85.0
    return lat_distance_km + lon_distance_km


def walking_minutes_from_distance_km(distance_km: float | None) -> int | None:
    """Convert distance in km to walking minutes at 5 km/h."""
    if distance_km is None:
        return None
    distance_value = max(0.0, _safe_float(distance_km, 0.0))
    return max(1, int(round((distance_value / WALKING_SPEED_KMPH) * 60.0)))


# Backward-compatible alias for existing imports in frontend modules.
haversine_km = manhattan_distance_km


def _with_distance_km(restaurants: list[dict], origin_lat: float | None = None, origin_lon: float | None = None) -> list[dict]:
    """Calculate distance from origin coordinates to each restaurant.
    
    Args:
        restaurants: List of restaurant dicts to enrich with distance_km
        origin_lat: Latitude of origin (defaults to NYU_LAT if not provided)
        origin_lon: Longitude of origin (defaults to NYU_LON if not provided)
    
    Returns:
        List of restaurants with added/updated distance_km field
    """
    # Use provided origin or fall back to NYU
    if origin_lat is None:
        origin_lat = NYU_LAT
    if origin_lon is None:
        origin_lon = NYU_LON
    
    enriched: list[dict] = []
    for restaurant in restaurants:
        item = dict(restaurant)
        coords = item.get("coordinates") or {}
        lat = _safe_float(item.get("latitude") or coords.get("latitude"), 0.0)
        lon = _safe_float(item.get("longitude") or coords.get("longitude"), 0.0)
        if lat and lon:
            item["distance_km"] = manhattan_distance_km(origin_lat, origin_lon, lat, lon)
            item["travel_minutes"] = walking_minutes_from_distance_km(item["distance_km"])
        else:
            item["distance_km"] = None
            item["travel_minutes"] = None
        enriched.append(item)
    return enriched


def _rank_by_location_and_rating(
    restaurants: list[dict],
    filters: dict,
    top_k: int,
) -> list[dict]:
    # Extract origin coordinates from filters if available, else use NYU
    origin_lat = _safe_float(filters.get("origin_lat"), NYU_LAT)
    origin_lon = _safe_float(filters.get("origin_lon"), NYU_LON)
    
    ranked = _with_distance_km(restaurants, origin_lat, origin_lon)
    ranked = apply_filters(ranked, filters)
    ranked = _apply_borough_filter(ranked, filters.get("borough"))

    ranked.sort(
        key=lambda item: (
            -_safe_float(item.get("rating"), 0.0),
            _safe_float(item.get("distance_km"), 1e9),
        )
    )

    for item in ranked:
        rating = _safe_float(item.get("rating"), 0.0)
        distance = _safe_float(item.get("distance_km"), 1e9)
        item["semantic_score"] = 0.0
        item["final_score"] = (rating * 0.8) + (max(0.0, 10.0 - min(distance, 10.0)) * 0.02)

    return ranked[:top_k]


def _get_restaurants() -> list[dict]:
    """Lazy-load and cache restaurant records."""
    global _restaurants
    if _restaurants is None:
        _restaurants = load_restaurants()
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
        or filters.get("price_levels")
        or filters.get("discover_prices")
        or []
    )

    min_rating = filters.get("min_rating")
    if min_rating is None:
        min_rating = filters.get("discover_min_rating", 0.0)

    max_distance_km = filters.get("max_distance_km")
    if max_distance_km is None and filters.get("discover_radius_minutes") is not None:
        try:
            max_distance_km = float(filters.get("discover_radius_minutes", 0)) * (WALKING_SPEED_KMPH / 60.0)
        except (TypeError, ValueError):
            max_distance_km = None

    borough = filters.get("borough")
    if borough is None:
        borough = filters.get("discover_borough", "All")

    origin_lat = filters.get("origin_lat")
    origin_lon = filters.get("origin_lon")
    dietary = filters.get("dietary") or filters.get("dietary_restrictions") or []
    if isinstance(dietary, str):
        dietary = [dietary]
    strict_dietary = bool(
        filters.get("strict_dietary")
        or filters.get("dietary_strict")
        or filters.get("strict_dietary_filter")
    )

    discover_categories = filters.get("discover_categories", [])
    discover_prices = filters.get("discover_prices", [])
    discover_min_rating = filters.get("discover_min_rating")
    discover_radius_minutes = filters.get("discover_radius_minutes")
    discover_borough = filters.get("discover_borough")

    explicit_cuisines = bool(cuisines)
    explicit_price = bool(prices)
    explicit_min_rating = filters.get("min_rating") is not None
    explicit_max_distance = (
        filters.get("max_distance_km") is not None
        or filters.get("discover_radius_minutes") is not None
    )
    explicit_borough = borough not in (None, "All")
    explicit_dietary = bool(dietary)

    if not explicit_cuisines and isinstance(discover_categories, list):
        explicit_cuisines = bool(discover_categories)
    if not explicit_price and isinstance(discover_prices, list):
        explicit_price = bool(discover_prices)
    if not explicit_min_rating and discover_min_rating is not None:
        explicit_min_rating = float(discover_min_rating) != 4.0
    if not explicit_borough and discover_borough is not None:
        explicit_borough = discover_borough != "All"

    return {
        "cuisines": list(cuisines) if isinstance(cuisines, list) else [],
        "price": list(prices) if isinstance(prices, list) else [],
        "min_rating": min_rating,
        "max_distance_km": max_distance_km,
        "borough": borough,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
        "dietary": list(dietary) if isinstance(dietary, list) else [],
        "strict_dietary": strict_dietary,
        "explicit_cuisines": explicit_cuisines,
        "explicit_price": explicit_price,
        "explicit_min_rating": explicit_min_rating,
        "explicit_max_distance": explicit_max_distance,
        "explicit_borough": explicit_borough,
        "explicit_dietary": explicit_dietary,
    }


def _normalize_borough_name(location: str | None) -> str | None:
    if not location:
        return None

    borough_aliases = {
        "manhattan": "Manhattan",
        "brooklyn": "Brooklyn",
        "queens": "Queens",
        "bronx": "Bronx",
        "staten island": "Staten_Island",
        "staten_island": "Staten_Island",
    }
    normalized_location = str(location).strip().replace("_", " ").lower()
    return borough_aliases.get(normalized_location)


def _merge_query_signals(filters: dict, parsed_query: dict[str, object]) -> dict:
    """Merge query signals without turning soft parsed hints into hard filters."""
    merged = dict(filters)

    parsed_location = parsed_query.get("location")
    if isinstance(parsed_location, dict):
        origin_lat = parsed_location.get("lat")
        origin_lon = parsed_location.get("lon")
        if origin_lat is not None and origin_lon is not None:
            if merged.get("origin_lat") is None:
                merged["origin_lat"] = origin_lat
            if merged.get("origin_lon") is None:
                merged["origin_lon"] = origin_lon
    elif isinstance(parsed_location, str) and parsed_location:
        coords = resolve_location_coordinate(parsed_location)
        if coords:
            origin_lat, origin_lon = coords
            if merged.get("origin_lat") is None:
                merged["origin_lat"] = origin_lat
            if merged.get("origin_lon") is None:
                merged["origin_lon"] = origin_lon

    return merged


def _parsed_location_label(parsed_location: object) -> str | None:
    if isinstance(parsed_location, dict):
        label = parsed_location.get("label")
        return str(label).strip() if label else None
    if isinstance(parsed_location, str) and parsed_location.strip():
        return parsed_location.strip()
    return None


def _first_filter_value(values: object) -> str | None:
    if isinstance(values, list):
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return None
    text = str(values or "").strip()
    return text or None


def _apply_borough_filter(restaurants: list[dict], borough: str | None) -> list[dict]:
    if not borough or borough == "All":
        return restaurants
    return [item for item in restaurants if item.get("borough") == borough]


def _restaurant_lat_lon(restaurant: dict) -> tuple[float | None, float | None]:
    coords = restaurant.get("coordinates") or {}
    lat = _safe_float(restaurant.get("latitude") or coords.get("latitude"), 0.0)
    lon = _safe_float(restaurant.get("longitude") or coords.get("longitude"), 0.0)
    if lat and lon:
        return lat, lon
    return None, None


def _filter_within_radius_km(
    restaurants: list[dict],
    center_lat: float,
    center_lon: float,
    max_km: float,
) -> list[dict]:
    """Keep restaurants whose coordinates fall within ``max_km`` of the center."""
    if max_km <= 0.0:
        return restaurants
    kept: list[dict] = []
    for item in restaurants:
        lat, lon = _restaurant_lat_lon(item)
        if lat is None or lon is None:
            continue
        if manhattan_distance_km(center_lat, center_lon, lat, lon) <= max_km:
            kept.append(item)
    return kept


def _restaurant_matches_dietary(restaurant: dict, dietary_terms: list[str]) -> bool:
    if not dietary_terms:
        return True

    searchable_parts: list[str] = []
    for key in ("name", "embedding_text", "document"):
        value = restaurant.get(key)
        if isinstance(value, str) and value.strip():
            searchable_parts.append(value.strip().lower())

    for key in ("categories", "tags"):
        values = restaurant.get(key, [])
        if isinstance(values, list):
            searchable_parts.extend(str(value).strip().lower() for value in values if str(value).strip())

    searchable_text = " ".join(searchable_parts)
    return any(str(term).strip().lower() in searchable_text for term in dietary_terms)


def _apply_hard_filters(restaurants: list[dict], filters: dict) -> list[dict]:
    filtered = apply_filters(restaurants, filters)
    filtered = _apply_borough_filter(filtered, filters.get("borough"))

    dietary = filters.get("dietary", [])
    if isinstance(dietary, list) and dietary:
        filtered = [
            item
            for item in filtered
            if _restaurant_matches_dietary(item, dietary)
        ]

    return filtered


def _build_filter_stages(
    adapted_filters: dict,
    parsed_query: dict[str, object] | None,
) -> tuple[dict, dict, dict]:
    explicit_hard_filters = {
        "cuisines": adapted_filters.get("cuisines", []) if adapted_filters.get("explicit_cuisines") else [],
        "price": adapted_filters.get("price", []) if adapted_filters.get("explicit_price") else [],
        "min_rating": adapted_filters.get("min_rating") if adapted_filters.get("explicit_min_rating") else None,
        "max_distance_km": adapted_filters.get("max_distance_km") if adapted_filters.get("explicit_max_distance") else None,
        "borough": adapted_filters.get("borough") if adapted_filters.get("explicit_borough") else None,
    }
    if adapted_filters.get("strict_dietary") and adapted_filters.get("explicit_dietary"):
        explicit_hard_filters["dietary"] = adapted_filters.get("dietary", [])

    query_hard_filters = dict(explicit_hard_filters)
    soft_preferences: dict[str, object] = {
        "cuisines": adapted_filters.get("cuisines", []) if adapted_filters.get("explicit_cuisines") else [],
        "cuisine": adapted_filters.get("cuisines", []) if adapted_filters.get("explicit_cuisines") else [],
        "dietary": adapted_filters.get("dietary", []) if adapted_filters.get("explicit_dietary") else [],
        "price": _first_filter_value(adapted_filters.get("price", [])) if adapted_filters.get("explicit_price") else None,
        "location": None,
        "borough": None,
        "origin_lat": adapted_filters.get("origin_lat"),
        "origin_lon": adapted_filters.get("origin_lon"),
        "nearby": False,
        "max_distance_km": adapted_filters.get("max_distance_km") if adapted_filters.get("explicit_max_distance") else None,
        "occasion_vibe": [],
        "vibe": [],
        "meal_context": [],
        "meal_type": None,
    }

    if not parsed_query:
        return explicit_hard_filters, query_hard_filters, soft_preferences

    dietary = parsed_query.get("dietary", [])
    if not adapted_filters.get("explicit_dietary") and isinstance(dietary, list) and dietary:
        soft_preferences["dietary"] = [
            str(item).strip().lower()
            for item in dietary
            if str(item).strip()
        ]

    distance_intent = parsed_query.get("distance_time_intent")
    if isinstance(distance_intent, dict):
        max_km = distance_intent.get("max_km")
        if max_km is None:
            max_minutes = distance_intent.get("max_minutes")
            if isinstance(max_minutes, (int, float)):
                max_km = float(max_minutes) * (WALKING_SPEED_KMPH / 60.0)
        if not adapted_filters.get("explicit_max_distance") and max_km is not None:
            soft_preferences["max_distance_km"] = max_km
        soft_preferences["nearby"] = bool(distance_intent.get("near_me") or max_km is not None)

    parsed_price = parsed_query.get("price")
    if (
        not adapted_filters.get("explicit_price")
        and isinstance(parsed_price, str)
        and parsed_price
        and parsed_price != "unknown"
    ):
        soft_preferences["price"] = parsed_price

    parsed_location = parsed_query.get("location")
    parsed_location_label = _parsed_location_label(parsed_location)
    if parsed_location_label:
        soft_preferences["location"] = parsed_location_label
        parsed_borough = _normalize_borough_name(parsed_location_label)
        if parsed_borough:
            soft_preferences["borough"] = parsed_borough

    parsed_cuisines = parsed_query.get("cuisine") or parsed_query.get("cuisines") or []
    if not adapted_filters.get("explicit_cuisines") and isinstance(parsed_cuisines, list):
        cleaned_cuisines = [str(item).strip().lower() for item in parsed_cuisines if str(item).strip()]
        soft_preferences["cuisine"] = cleaned_cuisines
        soft_preferences["cuisines"] = cleaned_cuisines

    parsed_vibes = parsed_query.get("vibe") or parsed_query.get("occasion_vibe") or []
    if isinstance(parsed_vibes, list):
        cleaned_vibes = [str(item).strip().lower() for item in parsed_vibes if str(item).strip()]
        soft_preferences["vibe"] = cleaned_vibes
        soft_preferences["occasion_vibe"] = cleaned_vibes

    parsed_meal_context = parsed_query.get("meal_context") or []
    if isinstance(parsed_meal_context, list):
        soft_preferences["meal_context"] = [
            str(item).strip().lower()
            for item in parsed_meal_context
            if str(item).strip()
        ]
    parsed_meal_type = parsed_query.get("meal_type")
    if isinstance(parsed_meal_type, str) and parsed_meal_type.strip():
        soft_preferences["meal_type"] = parsed_meal_type.strip().lower()

    place = parsed_query.get("in_near_place_filter")
    if isinstance(place, dict) and place.get("kind") == "borough" and place.get("borough"):
        query_hard_filters["borough"] = place["borough"]

    return explicit_hard_filters, query_hard_filters, soft_preferences


def _soft_match_score(restaurant: dict, soft_preferences: dict) -> float:
    score = 0.0

    soft_price = soft_preferences.get("price")
    if isinstance(soft_price, str) and soft_price.strip():
        restaurant_price = str(restaurant.get("price") or "").strip().lower()
        if restaurant_price == soft_price.strip().lower():
            score += 1.0

    soft_borough = soft_preferences.get("borough")
    if isinstance(soft_borough, str) and soft_borough.strip():
        if str(restaurant.get("borough") or "").strip().lower() == soft_borough.strip().lower():
            score += 1.0

    searchable_parts: list[str] = []
    for key in ("name", "embedding_text", "document"):
        value = restaurant.get(key)
        if isinstance(value, str) and value.strip():
            searchable_parts.append(value.strip().lower())
    for key in ("categories", "tags"):
        values = restaurant.get(key, [])
        if isinstance(values, list):
            searchable_parts.extend(str(value).strip().lower() for value in values if str(value).strip())
    searchable_text = " ".join(searchable_parts)

    soft_location = soft_preferences.get("location")
    if isinstance(soft_location, str) and soft_location.strip() and soft_location.strip().lower() in searchable_text:
        score += 1.0

    for key in ("occasion_vibe", "meal_context", "cuisines"):
        values = soft_preferences.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            normalized = str(value).strip().lower().replace("_", " ")
            if normalized and normalized in searchable_text:
                score += 1.0

    return score


def _apply_soft_preference_filter(restaurants: list[dict], soft_preferences: dict) -> list[dict]:
    if not restaurants:
        return []

    scored = [
        (restaurant, _soft_match_score(restaurant, soft_preferences))
        for restaurant in restaurants
    ]
    preferred = [restaurant for restaurant, score in scored if score > 0.0]
    if len(preferred) >= SOFT_FILTER_MIN_RESULTS:
        return preferred
    return list(restaurants)


def _build_user_embedding_if_available(user_id: str) -> list[float] | None:
    """Build a profile-based user embedding if the questionnaire/profile exists."""
    if not user_id or user_id == "anonymous":
        return None

    # Tier 1 & 2: profile-based embedding
    profile = get_user_profile(user_id)
    if profile:
        latest_embedding = profile.get("latest_embedding")
        if isinstance(latest_embedding, dict):
            vector = latest_embedding.get("vector")
            model = latest_embedding.get("model_name", "")
            if (isinstance(vector, list) and vector
                    and model == "sentence-transformers/multi-qa-mpnet-base-cos-v1"):
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

    return None


def _normalize_vector(vector: list[float] | None) -> list[float] | None:
    if not isinstance(vector, list) or not vector:
        return None

    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return None
    return [value / norm for value in vector]


def _blend_vectors(
    left: list[float] | None,
    right: list[float] | None,
    left_weight: float,
    right_weight: float,
) -> list[float] | None:
    if left is None:
        return _normalize_vector(right)
    if right is None:
        return _normalize_vector(left)
    if len(left) != len(right):
        return _normalize_vector(left)

    blended = [
        (left_weight * left_value) + (right_weight * right_value)
        for left_value, right_value in zip(left, right)
    ]
    return _normalize_vector(blended)


def _resolve_interaction_weight(record: dict) -> float:
    interaction_type = str(record.get("interaction_type") or "").strip().lower()
    if interaction_type == "review":
        review_signal = str(record.get("review_signal") or "").strip().lower()
        return float(INTERACTION_WEIGHTS.get(("review", review_signal), 0.0))
    return float(INTERACTION_WEIGHTS.get(interaction_type, 0.0))


def _build_interaction_vector(user_id: str) -> list[float] | None:
    if not user_id or user_id == "anonymous":
        return None

    interactions = load_user_interactions(user_id)
    if not interactions:
        return None

    cluster_index, _cluster_centroids = _get_cluster_assets()
    if cluster_index is not None:
        embedding_by_business_id = {
            str(item.get("business_id", "")): item.get("embedding")
            for item in cluster_index
            if isinstance(item, dict) and isinstance(item.get("embedding"), list) and item.get("embedding")
        }
    else:
        index, _restaurants = _get_index()
        embedding_by_business_id = {
            str(restaurant.get("business_id", "")): embedding
            for restaurant, embedding in index
            if isinstance(restaurant, dict) and isinstance(embedding, list) and embedding
        }

    weighted_sum: list[float] | None = None
    total_weight = 0.0

    for record in interactions:
        if not isinstance(record, dict):
            continue

        weight = _resolve_interaction_weight(record)
        if weight <= 0.0:
            continue

        business_id = str(record.get("business_id") or "").strip()
        embedding = embedding_by_business_id.get(business_id)
        if not embedding:
            continue

        if weighted_sum is None:
            weighted_sum = [0.0] * len(embedding)

        for index_value, component in enumerate(embedding):
            weighted_sum[index_value] += weight * component
        total_weight += weight

    if weighted_sum is None or total_weight <= 0.0:
        return None

    averaged = [value / total_weight for value in weighted_sum]
    return _normalize_vector(averaged)


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_restaurants(
    query: str,
    filters: dict | None,
    user_id: str = "anonymous",
    top_k: int = 20,
    user_vector_only: bool = False,
) -> list[dict]:
    """
    Full search pipeline: semantic retrieval → filtering → personalized ranking.

    Args:
        query:   Natural language query from the user.
        filters: Structured filter dict from the UI sidebar.
        user_id: Current user ID (for personalization). Defaults to anonymous.
        top_k:   Max number of results to return.
        user_vector_only: If True, ignore query and use only user vector (recommendation mode).

    Returns:
        Ordered list of restaurant dicts (best match first).
    """
    requested_top_k = max(1, int(top_k))

    query_text = (query or "").strip()

    # Step 1: build profile and interaction vectors, then combine into one user vector
    profile_vector = _build_user_embedding_if_available(user_id)
    interaction_vector = _build_interaction_vector(user_id)
    user_vector = _blend_vectors(
        profile_vector,
        interaction_vector,
        left_weight=PROFILE_VECTOR_WEIGHT,
        right_weight=INTERACTION_VECTOR_WEIGHT,
    )
    adapted_filters = _adapt_filters(filters)
    user_origin_provided = (
        adapted_filters.get("origin_lat") is not None
        and adapted_filters.get("origin_lon") is not None
    )

    # Mode split:
    # - recommendation mode: empty query -> user vector only (or location fallback)
    # - search mode: non-empty query -> parse query, then embed full query + fuse with user vector
    use_recommendation_mode = user_vector_only or not query_text
    parsed_query = None
    embedding_query_text = query_text
    explicit_hard_filters, query_hard_filters, soft_preferences = _build_filter_stages(
        adapted_filters,
        None,
    )

    if not use_recommendation_mode:
        # Parse structured signals for filtering and ranking
        parsed_query = parse_query(query_text)
        # Use minimally cleaned full query for embedding to preserve semantic content
        embedding_query_text = minimal_clean_query(query_text)
        # Merge structured signals into filters
        adapted_filters = _merge_query_signals(adapted_filters, parsed_query)
        explicit_hard_filters, query_hard_filters, soft_preferences = _build_filter_stages(
            adapted_filters,
            parsed_query,
        )

    has_resolved_origin = (
        adapted_filters.get("origin_lat") is not None
        and adapted_filters.get("origin_lon") is not None
    )
    if user_origin_provided:
        print("Using user-provided origin")
    elif has_resolved_origin:
        print("Using query-parsed origin")
    else:
        print("Using NYU fallback")

    if use_recommendation_mode:
        if user_vector is None:
            fallback_restaurants = _get_restaurants()
            explicit_fallback = _apply_hard_filters(fallback_restaurants, explicit_hard_filters)
            fallback_pool = explicit_fallback if explicit_fallback else fallback_restaurants
            return _rank_by_location_and_rating(
                restaurants=fallback_pool,
                filters=adapted_filters,
                top_k=requested_top_k,
            )

        query_vector = [0.0] * len(user_vector)
        fused_vector = fuse_vectors(query_vector, user_vector, alpha=1.0)
    else:
        query_vector = embed_query(embedding_query_text)
        fused_vector = fuse_vectors(query_vector, user_vector, alpha=PERSONALIZATION_ALPHA)

    # Step 3: retrieve semantic candidates (cluster-first, then within-cluster search)
    candidates = _retrieve_candidates_cluster_first(fused_vector, k=requested_top_k * 3)

    # Step 4: apply structured filters
    # Extract origin coordinates from adapted_filters if available (set by _merge_query_signals)
    origin_lat = _safe_float(adapted_filters.get("origin_lat"), NYU_LAT)
    origin_lon = _safe_float(adapted_filters.get("origin_lon"), NYU_LON)
    candidate_restaurants = _with_distance_km([r for r, _ in candidates], origin_lat, origin_lon)
    explicit_filtered = _apply_hard_filters(candidate_restaurants, explicit_hard_filters)
    hard_filtered = _apply_hard_filters(explicit_filtered, query_hard_filters)

    strict_in_near = isinstance(parsed_query, dict) and bool(parsed_query.get("in_near_place_filter"))
    if strict_in_near and isinstance(parsed_query, dict):
        place = parsed_query.get("in_near_place_filter")
        if isinstance(place, dict) and place.get("kind") == "neighborhood":
            center_lat = place.get("lat")
            center_lon = place.get("lon")
            radius_km = place.get("radius_km", 1.6)
            if isinstance(center_lat, (int, float)) and isinstance(center_lon, (int, float)):
                hard_filtered = _filter_within_radius_km(
                    hard_filtered,
                    float(center_lat),
                    float(center_lon),
                    float(radius_km) if isinstance(radius_km, (int, float)) else 1.6,
                )

    ranking_pool = hard_filtered
    if len(ranking_pool) < HARD_FILTER_FALLBACK_MIN_RESULTS and not strict_in_near:
        ranking_pool = explicit_filtered if explicit_filtered else candidate_restaurants

    # Step 5: Rebuild (restaurant, score) tuples after filtering
    score_map = {
        str(restaurant.get("business_id", "")): score
        for restaurant, score in candidates
        if isinstance(restaurant, dict)
    }

    filtered_with_scores = [
        (restaurant, score_map.get(str(restaurant.get("business_id", "")), 0.0))
        for restaurant in ranking_pool
    ]

    # Step 6: rank candidates
    ranked = rank_candidates(
        filtered_with_scores,
        user_price_pref=str(soft_preferences.get("price") or "") or None,
        active_filters=soft_preferences,
    )

    # Step 7: return top-k
    return ranked[:requested_top_k]


def get_all_restaurants() -> list[dict]:
    """Return the full cached restaurant list."""
    return list(_get_restaurants())


def debug_compare_queries(
    user_id: str,
    query_a: str,
    query_b: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> dict:
    """Debug helper: compare semantic relevance of two queries."""
    return {
        "query_a": search_restaurants(query_a, filters, user_id, top_k),
        "query_b": search_restaurants(query_b, filters, user_id, top_k),
    }
