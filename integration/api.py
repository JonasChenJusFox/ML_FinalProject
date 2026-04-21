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


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _with_distance_km(restaurants: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for restaurant in restaurants:
        item = dict(restaurant)
        lat = _safe_float(item.get("latitude"), 0.0)
        lon = _safe_float(item.get("longitude"), 0.0)
        if lat and lon:
            item["distance_km"] = haversine_km(NYU_LAT, NYU_LON, lat, lon)
        else:
            item["distance_km"] = None
        enriched.append(item)
    return enriched


def _rank_by_location_and_rating(
    restaurants: list[dict],
    filters: dict,
    top_k: int,
) -> list[dict]:
    ranked = _with_distance_km(restaurants)
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

    return {
        "cuisines": list(cuisines) if isinstance(cuisines, list) else [],
        "price": list(prices) if isinstance(prices, list) else [],
        "min_rating": min_rating,
        "max_distance_km": max_distance_km,
        "borough": borough,
    }


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

    Returns:
        Ordered list of restaurant dicts (best match first).
    """
    requested_top_k = max(1, int(top_k))

    query_text = (query or "").strip()

    # Step 1: load existing user embedding if available
    user_vector = _build_user_embedding_if_available(user_id)
    adapted_filters = _adapt_filters(filters)

    # Mode split:
    # - recommendation mode: empty query -> user vector only (or location fallback)
    # - search mode: non-empty query -> embed query + fuse with user vector
    use_recommendation_mode = user_vector_only or not query_text

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
        query_vector = embed_query(query_text)
        fused_vector = fuse_vectors(query_vector, user_vector, alpha=PERSONALIZATION_ALPHA)

    # Step 3: retrieve semantic candidates (cluster-first, then within-cluster search)
    candidates = _retrieve_candidates_cluster_first(fused_vector, k=requested_top_k * 3)

    # Step 4: apply structured filters
    candidate_restaurants = _with_distance_km([r for r, _ in candidates])
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
