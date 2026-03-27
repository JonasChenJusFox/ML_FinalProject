#!/usr/bin/env python3
"""
embeddings/vectorizer.py
Owner: Fidaa

Embedding and retrieval vectorizer for restaurant data.

This module provides core embedding and similarity search functionality.
It expects restaurant dicts with a 'document' field (semantic text representation).
"""

from sentence_transformers import SentenceTransformer


_model_cache = None


def get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Load and cache the SentenceTransformer embedding model.
    
    Args:
        model_name: Name of the SentenceTransformer model to use.
        
    Returns:
        Loaded SentenceTransformer model instance.
    """
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(model_name)
    return _model_cache


def _append_review_snippets(
    document: str,
    google_reviews,
    max_reviews: int = 3,
    review_char_limit: int = 300,
) -> str:
    """Append capped review snippets to a base document string."""
    if not isinstance(document, str):
        document = ""

    snippets = []
    if isinstance(google_reviews, list):
        for review in google_reviews:
            review_text = ""

            if isinstance(review, str):
                review_text = review.strip()
            elif isinstance(review, dict):
                for key in ("text", "review_text", "content", "snippet"):
                    value = review.get(key)
                    if isinstance(value, str) and value.strip():
                        review_text = value.strip()
                        break

            if not review_text:
                continue

            snippets.append(review_text[:review_char_limit])
            if len(snippets) >= max_reviews:
                break

    if not snippets:
        return document.strip()

    return f"{document.strip()}\n\nReview snippets: {' | '.join(snippets)}"


def embed_restaurant(restaurant: dict) -> list[float]:
    """Embed a restaurant record.
    
    Args:
        restaurant: Restaurant dict with a base 'document' field and optional
            'google_reviews' list.
        
    Returns:
        List of floats representing the normalized embedding vector (384-dimensional).
    """
    model = get_embedding_model()
    
    # Start from the existing document and append capped review snippets.
    document = restaurant.get("document", "")
    document = _append_review_snippets(document, restaurant.get("google_reviews", []))
    
    # Encode with normalization
    vector = model.encode(
        document,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vector.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a user query string.
    
    Args:
        query: User query text.
        
    Returns:
        List of floats representing the normalized embedding vector (384-dimensional).
    """
    model = get_embedding_model()
    vector = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vector.tolist()


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors from scratch.
    
    Args:
        vec1: First vector (list of floats).
        vec2: Second vector (list of floats).
        
    Returns:
        Cosine similarity score in range [0, 1] for normalized vectors.
    """
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    norm_vec1 = sum(v ** 2 for v in vec1) ** 0.5
    norm_vec2 = sum(v ** 2 for v in vec2) ** 0.5
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)


def build_restaurant_index(restaurants: list[dict]) -> list[tuple[dict, list[float]]]:
    """Build an index of restaurants with their embeddings.
    
    Args:
        restaurants: List of restaurant dicts.
        
    Returns:
        List of tuples (restaurant_dict, embedding_vector) for each restaurant.
    """
    index = []
    for restaurant in restaurants:
        embedding = embed_restaurant(restaurant)
        index.append((restaurant, embedding))
    return index


def retrieve_top_k(
    query_vector: list[float],
    index: list[tuple[dict, list[float]]],
    k: int,
) -> list[tuple[dict, float]]:
    """Retrieve top-k most similar restaurants for a query vector.
    
    Args:
        query_vector: Embedding vector for user query.
        index: Restaurant index from build_restaurant_index().
        k: Number of top results to return.
        
    Returns:
        List of tuples (restaurant_dict, similarity_score) sorted by score descending.
    """
    scored = []
    for restaurant, embedding in index:
        score = cosine_similarity(query_vector, embedding)
        scored.append((restaurant, score))
    
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]
