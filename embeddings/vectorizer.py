"""
embeddings/vectorizer.py
Owner: Fidaa

Responsibilities:
- Choose and load the embedding model
- Convert restaurant text fields into embedding vectors
- Embed incoming user queries
- Provide vector similarity search (cosine similarity implemented from scratch)
"""

from typing import Optional


def get_embedding_model():
    """
    Load and return the chosen embedding model.
    (e.g. sentence-transformers, OpenAI ada, etc.)
    """
    raise NotImplementedError("TODO (Fidaa): implement get_embedding_model()")


def embed_restaurant(restaurant: dict) -> list[float]:
    """
    Convert a restaurant record into an embedding vector.

    The text representation should combine relevant fields such as:
    name, categories, neighborhood, vibe tags, review snippets.

    Args:
        restaurant: Normalized restaurant dict from data/pipeline.py

    Returns:
        Embedding vector as a list of floats.
    """
    raise NotImplementedError("TODO (Fidaa): implement embed_restaurant()")


def embed_query(query: str) -> list[float]:
    """
    Convert a natural-language user query into an embedding vector.

    Args:
        query: Raw user input, e.g. "cozy brunch near NYU"

    Returns:
        Embedding vector as a list of floats.
    """
    raise NotImplementedError("TODO (Fidaa): implement embed_query()")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Implemented from scratch (no numpy/sklearn) to satisfy the
    course requirement for an algorithm implemented without libraries.

    Args:
        vec1: First embedding vector.
        vec2: Second embedding vector.

    Returns:
        Cosine similarity score in [-1, 1].
    """
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    norm_vec1 = sum(v ** 2 for v in vec1) ** 0.5
    norm_vec2 = sum(v ** 2 for v in vec2) ** 0.5
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)


def build_restaurant_index(restaurants: list[dict]) -> list[tuple[dict, list[float]]]:
    """
    Pre-compute embeddings for all restaurants and return an index.

    Args:
        restaurants: List of normalized restaurant dicts.

    Returns:
        List of (restaurant, embedding) tuples.
    """
    raise NotImplementedError("TODO (Fidaa): implement build_restaurant_index()")


def retrieve_top_k(
    query_vector: list[float],
    index: list[tuple[dict, list[float]]],
    k: int = 20,
) -> list[tuple[dict, float]]:
    """
    Retrieve the top-k restaurants by cosine similarity to the query vector.

    Args:
        query_vector: Embedded user query.
        index: Pre-built restaurant embedding index.
        k: Number of candidates to return.

    Returns:
        List of (restaurant, similarity_score) tuples, sorted descending.
    """
    raise NotImplementedError("TODO (Fidaa): implement retrieve_top_k()")
