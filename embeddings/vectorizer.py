#!/usr/bin/env python3
"""
embeddings/vectorizer.py
Owner: Fidaa

Core embedding utilities for the restaurant discovery pipeline.

Provides low-level embedding and similarity functions used across all modules.
All embeddings are normalized vectors.

NOTE: All modules (vectorizer, build_index, cluster_retrieval, user modeling)
must use the same model to ensure embedding spaces are compatible.
Default model: sentence-transformers/multi-qa-mpnet-base-cos-v1.
"""

from typing import Any


# NOTE: This cache assumes a single model is used across the entire pipeline.
# Calling get_embedding_model() with a different model_name after the first
# call will silently return the originally loaded model.
_model_cache: Any = None


def get_embedding_model(model_name: str = "sentence-transformers/multi-qa-mpnet-base-cos-v1") -> Any:
    """Load and cache the SentenceTransformer embedding model.

    Args:
        model_name: Name of the SentenceTransformer model to use.
                    All modules must use the same model name.

    Returns:
        Loaded SentenceTransformer model instance.
    """
    global _model_cache
    if _model_cache is None:
        from sentence_transformers import SentenceTransformer

        _model_cache = SentenceTransformer(model_name)
    return _model_cache


def embed_restaurant(restaurant: dict) -> list[float]:
    """Embed a restaurant record into a normalized vector.

    Uses the 'embedding_text' field, which contains a natural language summary
    of the restaurant including cuisine, price, rating, and sentiment analysis
    of food, service, and atmosphere derived from reviews.

    Args:
        restaurant: Restaurant dict with an 'embedding_text' field.

    Returns:
        Normalized embedding vector as a list of floats.
    """
    model = get_embedding_model()

    document = restaurant["embedding_text"]

    vector = model.encode(
        document,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vector.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a user query string into a normalized vector.

    Args:
        query: User query text.

    Returns:
        Normalized embedding vector as a list of floats.
    """
    model = get_embedding_model()
    vector = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vector.tolist()


def embed_user(user_document: str) -> list[float]:
    """Embed a user profile document into a normalized vector.

    The user_document should be a natural language representation of the
    user's preferences (constructed by the user modeling module).
    Must use the same model as embed_restaurant() and embed_query().

    Args:
        user_document: Natural language string capturing user preferences.

    Returns:
        Normalized embedding vector as a list of floats.
    """
    model = get_embedding_model()
    vector = model.encode(
        user_document,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vector.tolist()


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two normalized vectors.

    Args:
        vec1: First normalized vector (list of floats).
        vec2: Second normalized vector (list of floats).

    Returns:
        Cosine similarity score. Returns 0.0 if either vector is zero.
    """
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    norm_vec1 = sum(v ** 2 for v in vec1) ** 0.5
    norm_vec2 = sum(v ** 2 for v in vec2) ** 0.5
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)


def build_restaurant_index(restaurants: list[dict]) -> list[tuple[dict, list[float]]]:
    """Build an in-memory restaurant index of ``(restaurant, embedding)`` tuples.

    Reuses a pre-existing ``embedding`` field if present; otherwise computes
    embeddings from ``embedding_text``.
    """
    index: list[tuple[dict, list[float]]] = []
    to_embed: list[dict] = []

    for restaurant in restaurants:
        if not isinstance(restaurant, dict):
            continue

        vector = restaurant.get("embedding")
        if isinstance(vector, list) and vector:
            index.append((restaurant, vector))
            continue

        if "embedding_text" in restaurant:
            to_embed.append(restaurant)

    if not to_embed:
        return index

    model = get_embedding_model()
    documents = [restaurant["embedding_text"] for restaurant in to_embed]

    try:
        vectors = model.encode(
            documents,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).tolist()
        for restaurant, vector in zip(to_embed, vectors):
            index.append((restaurant, vector))
        return index
    except Exception:
        for restaurant in to_embed:
            try:
                index.append((restaurant, embed_restaurant(restaurant)))
            except Exception:
                continue
        return index


def retrieve_top_k(
    query_vector: list[float],
    index: list[tuple[dict, list[float]]],
    k: int = 20,
) -> list[tuple[dict, float]]:
    """Retrieve top-k restaurants by cosine similarity."""
    if not query_vector or not index:
        return []

    scored: list[tuple[dict, float]] = []
    for restaurant, embedding in index:
        if not isinstance(embedding, list) or not embedding:
            continue
        score = cosine_similarity(query_vector, embedding)
        scored.append((restaurant, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[: max(1, int(k))]
