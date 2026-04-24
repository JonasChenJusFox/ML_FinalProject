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
DEFAULT_NEARBY_DISTANCE_KM = 5.0
WALKING_SPEED_KMPH = 5.0


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

    return {
        "cuisines": list(cuisines) if isinstance(cuisines, list) else [],
        "price": list(prices) if isinstance(prices, list) else [],
        "min_rating": min_rating,
        "max_distance_km": max_distance_km,
        "borough": borough,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
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
    """Merge parsed query signals into filters, resolving location to coordinates if available."""
    merged = dict(filters)

    parsed_price = parsed_query.get("price")
    if isinstance(parsed_price, str) and parsed_price and parsed_price != "unknown" and not merged.get("price"):
        merged["price"] = [parsed_price]

    # Extract parsed location and try to resolve to coordinates
    parsed_location = parsed_query.get("location")
    if isinstance(parsed_location, str) and parsed_location:
        # Try to resolve location to coordinates (neighborhood -> centroid, keyword -> neighborhood -> centroid)
        coords = resolve_location_coordinate(parsed_location)
        if coords:
            # Store origin coordinates for distance calculation
            origin_lat, origin_lon = coords
            if merged.get("origin_lat") is None:
                merged["origin_lat"] = origin_lat
            if merged.get("origin_lon") is None:
                merged["origin_lon"] = origin_lon
        
        # Also normalize to borough for filtering (fallback/additional)
        borough = _normalize_borough_name(parsed_location)
        if borough and (not merged.get("borough") or merged.get("borough") == "All"):
            merged["borough"] = borough

    distance_intent = parsed_query.get("distance_time_intent")
    if isinstance(distance_intent, dict) and merged.get("max_distance_km") is None:
        max_distance_km = distance_intent.get("max_km")
        if max_distance_km is None:
            max_minutes = distance_intent.get("max_minutes")
            if isinstance(max_minutes, (int, float)):
                max_distance_km = float(max_minutes) * (WALKING_SPEED_KMPH / 60.0)
            elif distance_intent.get("near_me"):
                max_distance_km = DEFAULT_NEARBY_DISTANCE_KM

        if max_distance_km is not None:
            merged["max_distance_km"] = max_distance_km

    return merged


def _apply_borough_filter(restaurants: list[dict], borough: str | None) -> list[dict]:
    if not borough or borough == "All":
        return restaurants
    return [item for item in restaurants if item.get("borough") == borough]


def _build_user_embedding_if_available(user_id: str) -> list[float] | None:
    """Build user embedding with three-tier fallback:
    1. Stored latest_embedding from profile (fastest)
    2. Rebuild from profile_text and persist
    3. Build from interaction history (for users without a profile)
    """
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

    # Tier 3: fall back to interaction history
    interactions = load_user_interactions(user_id)
    if not interactions:
        return None

    tags: list[str] = []
    actions: list[str] = []
    for record in interactions:
        if not isinstance(record, dict):
            continue
        interaction_type = record.get("interaction_type")
        if isinstance(interaction_type, str) and interaction_type.strip():
            actions.append(interaction_type.strip())
        inferred_tags = record.get("inferred_food_tags", [])
        if isinstance(inferred_tags, list):
            tags.extend(str(tag).strip() for tag in inferred_tags if str(tag).strip())

    if not tags and not actions:
        return None

    try:
        return embed_user(" ".join(tags + actions))
    except Exception:
        return None


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

    # Step 1: load existing user embedding if available
    user_vector = _build_user_embedding_if_available(user_id)
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

    if not use_recommendation_mode:
        # Parse structured signals for filtering and ranking
        parsed_query = parse_query(query_text)
        # Use minimally cleaned full query for embedding to preserve semantic content
        embedding_query_text = minimal_clean_query(query_text)
        # Merge structured signals into filters
        adapted_filters = _merge_query_signals(adapted_filters, parsed_query)

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
            return _rank_by_location_and_rating(
                restaurants=fallback_restaurants,
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
    filtered = apply_filters(candidate_restaurants, adapted_filters)
    filtered = _apply_borough_filter(filtered, adapted_filters.get("borough"))

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
