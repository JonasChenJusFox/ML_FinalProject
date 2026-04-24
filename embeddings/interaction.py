"""Build interaction-based user embeddings from historical behavior.

This module computes a user vector as a weighted average of restaurant
embeddings using saved/liked interactions and review sentiment signals.
The final vector is L2-normalized to unit length.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
RESTAURANT_EMBEDDINGS_PATH = REPO_ROOT / "data" / "restaurant_embeddings.json"

ACTION_WEIGHTS: dict[str, float] = {
    "saved": 0.5,
    "liked": 1.5,
    "unsaved": 0.0,  # Explicitly ignored in scoring.
}

REVIEW_WEIGHTS: dict[str, float] = {
    "love": 3.0,
    "neutral": 0.5,
    "hate": -2.0,
}


def _load_restaurant_embedding_map() -> dict[str, list[float]]:
    """Load restaurant embeddings and index them by business_id."""
    if not RESTAURANT_EMBEDDINGS_PATH.exists():
        return {}

    with RESTAURANT_EMBEDDINGS_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        return {}

    embedding_map: dict[str, list[float]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue

        business_id = str(item.get("business_id", "")).strip()
        embedding = item.get("embedding")
        if not business_id or not isinstance(embedding, list):
            continue

        numeric_embedding: list[float] = []
        valid = True
        for value in embedding:
            try:
                numeric_embedding.append(float(value))
            except (TypeError, ValueError):
                valid = False
                break

        if valid and numeric_embedding:
            embedding_map[business_id] = numeric_embedding

    return embedding_map


def _resolve_interaction_getter() -> Callable[[str], list[dict]]:
    """Resolve a callable for fetching user interactions.

    Expected final interface:
    - integration.interaction_repo.get_user_interactions(username)

    Current compatibility fallback:
    - integration.wrapped_repo.get_user_interactions(username)
    """
    try:
        from integration.interaction_repo import get_user_interactions  # type: ignore

        return get_user_interactions
    except Exception:
        pass

    try:
        from integration.wrapped_repo import get_user_interactions

        return get_user_interactions
    except Exception:

        def _empty_interactions(_: str) -> list[dict]:
            return []

        return _empty_interactions


def _resolve_review_getter() -> Callable[[str], list[dict]]:
    """Resolve a callable for fetching user reviews.

    Expected final interface:
    - integration.review_repo.get_user_reviews(username)

    If unavailable, return an empty list so this module remains usable.
    """
    try:
        from integration.review_repo import get_user_reviews  # type: ignore

        return get_user_reviews
    except Exception:

        def _empty_reviews(_: str) -> list[dict]:
            return []

        return _empty_reviews


def _aggregate_weights(username: str) -> dict[str, float]:
    """Aggregate interaction and review weights per business_id."""
    get_user_interactions = _resolve_interaction_getter()
    get_user_reviews = _resolve_review_getter()

    interaction_rows = get_user_interactions(username) or []
    review_rows = get_user_reviews(username) or []

    aggregated: dict[str, float] = {}

    for row in interaction_rows:
        if not isinstance(row, dict):
            continue

        business_id = str(row.get("business_id", "")).strip()
        action = str(row.get("action", "")).strip().lower()
        if not business_id or action == "unsaved":
            continue

        weight = ACTION_WEIGHTS.get(action)
        if weight is None:
            continue

        aggregated[business_id] = aggregated.get(business_id, 0.0) + weight

    for row in review_rows:
        if not isinstance(row, dict):
            continue

        business_id = str(row.get("business_id", "")).strip()
        sentiment = str(row.get("sentiment", "")).strip().lower()
        if not business_id:
            continue

        weight = REVIEW_WEIGHTS.get(sentiment)
        if weight is None:
            continue

        aggregated[business_id] = aggregated.get(business_id, 0.0) + weight

    # Restaurants with net-zero contribution do not affect the weighted average.
    return {
        business_id: weight
        for business_id, weight in aggregated.items()
        if not math.isclose(weight, 0.0, abs_tol=1e-12)
    }


def _normalize(vector: list[float]) -> list[float] | None:
    """Return an L2-normalized copy of vector, or None if norm is zero."""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return None
    return [value / norm for value in vector]


def compute_interaction_vector(username: str) -> list[float] | None:
    """Compute an interaction-based user embedding.

    The computation is:
    1. Sum all interaction/review weights per restaurant.
    2. Multiply each restaurant embedding by its signed weight and sum.
    3. Divide by sum(abs(weight)) to get an absolute-weight average.
    4. L2-normalize the result to unit length.

    Args:
        username: Target user identifier.

    Returns:
        A normalized 768-dimensional vector if interactions are available,
        otherwise ``None``.

    Assumptions:
        The "liked" action and review sentiment states are not fully wired in
        the current repository yet. This implementation targets the expected
        final interface from teammates.

    TODO:
        Verify field names and value enums once the interaction/review schema
        is finalized by the teammate responsible for repo updates.
    """
    if not str(username or "").strip():
        return None

    business_weights = _aggregate_weights(username)
    if not business_weights:
        return None

    embedding_map = _load_restaurant_embedding_map()
    if not embedding_map:
        return None

    numerator: list[float] | None = None
    denominator = 0.0

    for business_id, weight in business_weights.items():
        embedding = embedding_map.get(business_id)
        if embedding is None:
            continue

        if len(embedding) != 768:
            continue

        if numerator is None:
            numerator = [0.0] * len(embedding)

        # Weighted average numerator:
        # add (weight * embedding_i) for every dimension i.
        for index, value in enumerate(embedding):
            numerator[index] += weight * value

        # Denominator uses absolute weights so positive/negative evidence
        # both contribute to confidence/magnitude of averaging.
        denominator += abs(weight)

    if numerator is None or denominator <= 0.0:
        return None

    averaged = [value / denominator for value in numerator]
    return _normalize(averaged)
