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

from data.pipeline import load_restaurants, load_user_interactions
from embeddings.vectorizer import embed_query, build_restaurant_index, retrieve_top_k
from recommendation.ranker import apply_filters, rank_candidates

# ---------------------------------------------------------------------------
# Module-level cache (populated on first call)
# ---------------------------------------------------------------------------
_restaurant_index = None
_restaurants = None


def _get_index():
    """Lazy-load and cache the restaurant embedding index."""
    global _restaurant_index, _restaurants
    if _restaurant_index is None:
        _restaurants = load_restaurants()
        _restaurant_index = build_restaurant_index(_restaurants)
    return _restaurant_index, _restaurants


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_restaurants(
    query: str,
    filters: dict,
    user_id: str = "anonymous",
    top_k: int = 20,
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
    # Step 1: embed the query
    query_vector = embed_query(query)

    # Step 2: retrieve semantic candidates
    index, _ = _get_index()
    candidates = retrieve_top_k(query_vector, index, k=top_k * 3)

    # Step 3: apply structured filters
    candidate_restaurants = [r for r, _ in candidates]
    filtered = apply_filters(candidate_restaurants, filters)

    # Rebuild (restaurant, score) tuples after filtering
    score_map = {id(r): score for r, score in candidates}
    filtered_with_scores = [(r, score_map.get(id(r), 0.0)) for r in filtered]

    # Step 4: load user history and rank
    user_history = load_user_interactions(user_id) if user_id != "anonymous" else []
    ranked = rank_candidates(filtered_with_scores, user_history)

    return ranked[:top_k]


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
