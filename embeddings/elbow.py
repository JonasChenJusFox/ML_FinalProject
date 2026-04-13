#!/usr/bin/env python3
"""
embeddings/elbow.py
Owner: Fidaa

Elbow method for justifying the choice of K in K-Means clustering.

Runs K-Means for a range of K values, computes inertia for each
(sum of cosine distances from each embedding to its assigned centroid),
and plots inertia vs K so the optimal K can be identified visually.

The elbow point — where inertia stops decreasing sharply — is the
recommended value of K to use in build_index.py.

Usage:
    python -m embeddings.elbow --input data/restaurants.json
"""

import argparse
import json

import matplotlib.pyplot as plt

from embeddings.vectorizer import cosine_similarity, embed_restaurant
from embeddings.build_index import kmeans_cluster


def load_restaurants(filepath: str) -> list[dict]:
    """Load restaurant records from a JSON file.

    Args:
        filepath: Path to the restaurants JSON file.

    Returns:
        List of restaurant dicts.
    """
    with open(filepath, "r") as f:
        restaurants = json.load(f)
    print(f"Loaded {len(restaurants)} restaurants from {filepath}")
    return restaurants


def compute_inertia(
    embeddings: list[list[float]],
    assignments: list[int],
    centroids: list[list[float]],
) -> float:
    """Compute inertia as the sum of cosine distances to assigned centroids.

    Uses cosine distance (1 - cosine_similarity) so that lower inertia
    means tighter, more coherent clusters.

    Args:
        embeddings: List of normalized embedding vectors.
        assignments: Cluster ID assigned to each embedding.
        centroids: List of centroid vectors.

    Returns:
        Total inertia as a float.
    """
    total = 0.0
    for vec, cluster_id in zip(embeddings, assignments):
        similarity = cosine_similarity(vec, centroids[cluster_id])
        total += 1.0 - similarity
    return total


def run_elbow(
    embeddings: list[list[float]],
    k_values: list[int],
) -> list[float]:
    """Run K-Means for each value of K and compute inertia.

    Args:
        embeddings: List of normalized embedding vectors.
        k_values: List of K values to evaluate.

    Returns:
        List of inertia values corresponding to each K.
    """
    inertias = []
    for k in k_values:
        print(f"Running K-Means with k={k}...")
        assignments, centroids = kmeans_cluster(embeddings, k=k)
        inertia = compute_inertia(embeddings, assignments, centroids)
        inertias.append(inertia)
        print(f"  k={k} → inertia={inertia:.4f}")
    return inertias


def plot_elbow(k_values: list[int], inertias: list[float]) -> None:
    """Plot inertia vs K and display interactively.

    Args:
        k_values: List of K values evaluated.
        inertias: Corresponding inertia values.
    """
    plt.figure(figsize=(8, 5))
    plt.plot(k_values, inertias, marker="o", linewidth=2, markersize=6)
    plt.xlabel("Number of clusters (K)")
    plt.ylabel("Inertia (sum of cosine distances)")
    plt.title("Elbow method — choosing K for restaurant clustering")
    plt.xticks(k_values)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Elbow method for K selection.")
    parser.add_argument(
        "--input",
        type=str,
        default="data/restaurants.json",
        help="Path to input restaurants JSON file.",
    )
    parser.add_argument(
        "--k-min",
        type=int,
        default=5,
        help="Minimum K value to evaluate (default 5).",
    )
    parser.add_argument(
        "--k-max",
        type=int,
        default=40,
        help="Maximum K value to evaluate (default 40).",
    )
    parser.add_argument(
        "--k-step",
        type=int,
        default=5,
        help="Step size between K values (default 5).",
    )
    args = parser.parse_args()

    k_values = list(range(args.k_min, args.k_max + 1, args.k_step))
    print(f"Evaluating K values: {k_values}")

    restaurants = load_restaurants(args.input)

    print("Embedding restaurants...")
    embeddings = []
    for i, restaurant in enumerate(restaurants):
        embeddings.append(embed_restaurant(restaurant))
        if (i + 1) % 100 == 0:
            print(f"  Embedded {i + 1}/{len(restaurants)}")
    print(f"Done. Embedded {len(embeddings)} restaurants.")

    inertias = run_elbow(embeddings, k_values)
    plot_elbow(k_values, inertias)


if __name__ == "__main__":
    main()
