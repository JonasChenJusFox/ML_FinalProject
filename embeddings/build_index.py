#!/usr/bin/env python3
"""Offline K-means over restaurant embeddings; writes ``restaurant_embeddings.json`` and ``cluster_centroids.json``.

Run when the corpus changes before serving search. Example:
``python -m embeddings.build_index --input data/restaurants.json --k 20``.
"""

import argparse
import json
import random

from embeddings.vectorizer import cosine_similarity, embed_restaurant

def load_restaurants(filepath: str) -> list[dict]:
    """Load restaurant records from a JSON file.

    Args:
        filepath: Path to the restaurants JSON file. Expected to be a list
                  of restaurant dicts, each with an 'embedding_text' field.

    Returns:
        List of restaurant dicts.
    """
    with open(filepath, "r") as f:
        restaurants = json.load(f)
    print(f"Loaded {len(restaurants)} restaurants from {filepath}")
    return restaurants


def kmeans_cluster(
    embeddings: list[list[float]],
    k: int,
    max_iters: int = 100,
    seed: int = 42,
) -> tuple[list[int], list[list[float]]]:
    """Run K-Means clustering on a list of embedding vectors.

    Implemented from scratch using Lloyd's algorithm.

    Args:
        embeddings: List of normalized embedding vectors.
        k: Number of clusters.
        max_iters: Maximum number of iterations before stopping.
        seed: Random seed for reproducible centroid initialization.

    Returns:
        Tuple of (assignments, centroids) where:
            assignments: List of cluster IDs (int), one per embedding.
            centroids: List of k centroid vectors.
    """
    random.seed(seed)
    n = len(embeddings)
    dim = len(embeddings[0])

    # Initialize centroids by picking k random embeddings
    centroid_indices = random.sample(range(n), k)
    centroids = [embeddings[i][:] for i in centroid_indices]

    assignments = [0] * n

    for iteration in range(max_iters):
        # Assignment step: assign each embedding to its nearest centroid
        new_assignments = []
        for vec in embeddings:
            best_cluster = 0
            best_score = -1.0
            for cluster_id, centroid in enumerate(centroids):
                score = cosine_similarity(vec, centroid)
                if score > best_score:
                    best_score = score
                    best_cluster = cluster_id
            new_assignments.append(best_cluster)

        # Check for convergence
        if new_assignments == assignments:
            print(f"K-Means converged at iteration {iteration + 1}")
            break
        assignments = new_assignments

        # Update step: recompute centroids as mean of assigned embeddings
        new_centroids = [[0.0] * dim for _ in range(k)]
        counts = [0] * k
        for vec, cluster_id in zip(embeddings, assignments):
            for i, v in enumerate(vec):
                new_centroids[cluster_id][i] += v
            counts[cluster_id] += 1

        for cluster_id in range(k):
            if counts[cluster_id] == 0:
                # Reinitialize empty cluster to a random embedding
                new_centroids[cluster_id] = embeddings[random.randint(0, n - 1)][:]
            else:
                count = counts[cluster_id]
                new_centroids[cluster_id] = [
                    v / count for v in new_centroids[cluster_id]
                ]

        centroids = new_centroids
    else:
        print(f"K-Means reached max iterations ({max_iters})")

    return assignments, centroids


def build_and_save_index(
    restaurants: list[dict],
    k: int,
    embeddings_output: str = "data/restaurant_embeddings.json",
    centroids_output: str = "data/cluster_centroids.json",
) -> None:
    """Embed all restaurants, cluster them, and save results to disk.

    Args:
        restaurants: List of restaurant dicts with 'embedding_text' fields.
        k: Number of clusters for K-Means.
        embeddings_output: Path to save restaurant embeddings JSON.
        centroids_output: Path to save cluster centroids JSON.
    """
    # Step 1: Embed all restaurants
    print("Embedding restaurants...")
    embeddings = []
    for i, restaurant in enumerate(restaurants):
        embedding = embed_restaurant(restaurant)
        embeddings.append(embedding)
        if (i + 1) % 100 == 0:
            print(f"  Embedded {i + 1}/{len(restaurants)}")
    print(f"Done. Embedded {len(embeddings)} restaurants.")

    # Step 2: Run K-Means clustering
    print(f"Running K-Means with k={k}...")
    assignments, centroids = kmeans_cluster(embeddings, k=k)

    cluster_counts = {}
    for cluster_id in assignments:
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    print(f"Cluster sizes: min={min(cluster_counts.values())}, "
          f"max={max(cluster_counts.values())}, "
          f"avg={sum(cluster_counts.values()) / len(cluster_counts):.1f}")

    # Step 3: Save restaurant embeddings with cluster assignments and
    # ranker-friendly metadata fields.
    print(f"Saving restaurant embeddings to {embeddings_output}...")
    restaurant_index = []
    for restaurant, embedding, cluster_id in zip(restaurants, embeddings, assignments):
        restaurant_index.append({
            "business_id": restaurant["business_id"],
            "name": restaurant.get("name"),
            "embedding": embedding,
            "cluster_id": cluster_id,
            "rating": restaurant.get("rating"),
            "review_count": restaurant.get("review_count"),
            "price": restaurant.get("price"),
            "distance_km": restaurant.get("distance_km"),
            "categories": restaurant.get("categories", []),
        })
    with open(embeddings_output, "w") as f:
        json.dump(restaurant_index, f)
    print(f"Saved {len(restaurant_index)} entries to {embeddings_output}")

    # Step 4: Save cluster centroids as a mapping for ranker compatibility
    print(f"Saving cluster centroids to {centroids_output}...")
    centroid_data = {
        cluster_id: centroid
        for cluster_id, centroid in enumerate(centroids)
    }
    with open(centroids_output, "w") as f:
        json.dump(centroid_data, f)
    print(f"Saved {len(centroid_data)} centroids to {centroids_output}")


def main():
    parser = argparse.ArgumentParser(description="Build restaurant embedding index.")
    parser.add_argument(
        "--input",
        type=str,
        default="data/restaurants.json",
        help="Path to input restaurants JSON file.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=20,
        help="Number of clusters for K-Means.",
    )
    parser.add_argument(
        "--embeddings-output",
        type=str,
        default="data/restaurant_embeddings.json",
        help="Path to save restaurant embeddings.",
    )
    parser.add_argument(
        "--centroids-output",
        type=str,
        default="data/cluster_centroids.json",
        help="Path to save cluster centroids.",
    )
    args = parser.parse_args()

    restaurants = load_restaurants(args.input)
    build_and_save_index(
        restaurants,
        k=args.k,
        embeddings_output=args.embeddings_output,
        centroids_output=args.centroids_output,
    )
    print("Index build complete.")


if __name__ == "__main__":
    main()
