#!/usr/bin/env python3
"""
embeddings/cluster_retrieval.py
Owner: Fidaa

Cluster-based retrieval for the restaurant discovery pipeline.

Loads precomputed restaurant embeddings and cluster centroids from disk,
then at query time finds the nearest cluster and returns the top-k most
similar restaurants within that cluster as candidates for re-ranking.

This module is the handoff point between the embedding/retrieval layer
and the user modeling + ranking layer. Its output is a shortlist of
~20 candidates passed to ranking.py for personalized re-ranking.
"""

import json
import logging
import argparse

from embeddings.vectorizer import cosine_similarity, embed_query

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------

def load_restaurant_index(filepath: str = "data/restaurant_embeddings.json") -> list[dict]:
    """Load precomputed restaurant embeddings from disk.

    Args:
        filepath: Path to the restaurant embeddings JSON file produced
                  by build_index.py.

    Returns:
        List of dicts with keys: business_id, embedding, cluster_id.
    """
    with open(filepath, "r") as f:
        index = json.load(f)
    logger.info("Loaded %d restaurant embeddings from %s", len(index), filepath)
    return index


def load_centroids(filepath: str = "data/cluster_centroids.json") -> list[dict]:
    """Load precomputed cluster centroids from disk.

    Args:
        filepath: Path to the cluster centroids JSON file produced
                  by build_index.py.

    Returns:
        List of dicts with keys: cluster_id, centroid.
    """
    with open(filepath, "r") as f:
        centroids = json.load(f)
    logger.info("Loaded %d cluster centroids from %s", len(centroids), filepath)
    return centroids


# ---------------------------------------------------------------------------
# Cluster selection
# ---------------------------------------------------------------------------

def find_nearest_clusters(
    query_vector: list[float],
    centroids: list[dict],
    top_n: int = 2, #Just added
) -> list[int]:
    """Find the cluster whose centroid is most similar to the query vector.

    Args:
        query_vector: Normalized embedding vector for the query.
        centroids: List of centroid dicts with keys: cluster_id, centroid.

    Returns:
        cluster_id of the nearest centroid.
    """
    '''
    best_cluster_id = 0
    best_score = -1.0

    for entry in centroids:
        score = cosine_similarity(query_vector, entry["centroid"])
        if score > best_score:
            best_score = score
            best_cluster_id = entry["cluster_id"]

    return best_cluster_id
    '''
    scored = []
    for entry in centroids:
        score = cosine_similarity(query_vector, entry["centroid"])
        scored.append((entry["cluster_id"], score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [cluster_id for cluster_id, _ in scored[:top_n]]


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_candidates(
    query_vector: list[float],
    index: list[dict],
    centroids: list[dict],
    k: int = 20,
) -> list[tuple[str, float, int]]:
    """Retrieve top-k restaurant candidates using cluster-based retrieval.

    Finds the nearest cluster to the query vector, then scores all
    restaurants within that cluster by cosine similarity and returns
    the top-k results.

    Args:
        query_vector: Normalized embedding vector for the query.
        index: Restaurant index loaded from load_restaurant_index().
        centroids: Cluster centroids loaded from load_centroids().
        k: Number of top candidates to return (default 20).

    Returns:
        List of tuples (business_id, similarity_score, cluster_id),
        sorted by similarity score descending.
    """
    nearest_clusters = find_nearest_clusters(query_vector, centroids)

    # Filter index to restaurants in the nearest cluster
    '''cluster_entries = [
        entry for entry in index
        if entry["cluster_id"] == nearest_cluster
    ]'''
    cluster_entries = [
    entry for entry in index
    if entry["cluster_id"] in nearest_clusters
]

    # Score each restaurant in the cluster
    scored = []
    for entry in cluster_entries:
        score = cosine_similarity(query_vector, entry["embedding"])
        scored.append((entry["business_id"], score, entry["cluster_id"]))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]


def retrieve_candidates_from_query(
    query: str,
    index: list[dict],
    centroids: list[dict],
    k: int = 20,
) -> list[tuple[str, float, int]]:
    """Convenience wrapper: embed a raw query string and retrieve candidates.

    This is the main entry point for the ranking module. Takes a raw query
    string, handles embedding internally, and returns the top-k candidates.

    Args:
        query: Raw user query string.
        index: Restaurant index loaded from load_restaurant_index().
        centroids: Cluster centroids loaded from load_centroids().
        k: Number of top candidates to return (default 20).

    Returns:
        List of tuples (business_id, similarity_score, cluster_id),
        sorted by similarity score descending.
    """
    query_vector = embed_query(query)
    return retrieve_candidates(query_vector, index, centroids, k=k)


def main() -> None:
    """Run cluster retrieval from the command line.

    Example:
        python -m embeddings.cluster_retrieval --query "cozy japanese spot" --k 5
    """
    parser = argparse.ArgumentParser(
        description="Retrieve top-k restaurant candidates for a query."
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Natural language query string.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=20,
        help="Number of top results to return (default 20).",
    )
    parser.add_argument(
        "--index-path",
        type=str,
        default="data/restaurant_embeddings.json",
        help="Path to restaurant embeddings JSON.",
    )
    parser.add_argument(
        "--centroids-path",
        type=str,
        default="data/cluster_centroids.json",
        help="Path to cluster centroids JSON.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default WARNING).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))

    index = load_restaurant_index(args.index_path)
    centroids = load_centroids(args.centroids_path)
    results = retrieve_candidates_from_query(args.query, index, centroids, k=args.k)

    if not results:
        print("No candidates found.")
        return

    for rank, (business_id, score, cluster_id) in enumerate(results, start=1):
        print(f"{rank}. {business_id} | score={score:.4f} | cluster={cluster_id}")


if __name__ == "__main__":
    main()
