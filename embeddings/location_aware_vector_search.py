#!/usr/bin/env python3
"""Location-aware semantic search built on top of vectorizer.py.

This module keeps location logic separate from vectorizer primitives:
- Detect borough and neighborhood intent in user queries
- Optionally boost same-borough candidates during ranking
- Run semantic retrieval over data/restaurants_with_google_reviews_final.json
"""

import argparse
import json
import re
from pathlib import Path

import vectorizer


BOROUGH_ALIASES = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "staten island": "Staten_Island",
    "staten_island": "Staten_Island",
}

DEFAULT_RESTAURANTS_PATH = Path("data/restaurants_with_google_reviews_final.json")
REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_LOCATION_DICT_PATH = REPO_ROOT / "config" / "neighborhood_to_borough_nyc.json"


def normalize_query_text(text: str) -> str:
    """Normalize text for robust token/substring matching."""
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def load_neighborhood_mapping(path: Path) -> dict[str, str]:
    """Load neighborhood -> borough mapping from JSON."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Location mapping must be a JSON object.")

    mapping: dict[str, str] = {}
    for neighborhood, borough in payload.items():
        if isinstance(neighborhood, str) and isinstance(borough, str):
            mapping[normalize_query_text(neighborhood)] = borough

    if not mapping:
        raise ValueError("Location mapping is empty or invalid.")

    return mapping


def detect_location_intent(
    query: str,
    neighborhood_to_borough: dict[str, str],
) -> tuple[set[str], set[str]]:
    """Detect borough mentions and map neighborhood mentions to boroughs."""
    normalized_query = normalize_query_text(query)

    detected_boroughs = set()
    detected_neighborhoods = set()

    for alias, borough in BOROUGH_ALIASES.items():
        if alias in normalized_query:
            detected_boroughs.add(borough)

    for neighborhood, borough in neighborhood_to_borough.items():
        if neighborhood in normalized_query:
            detected_neighborhoods.add(neighborhood)
            detected_boroughs.add(borough)

    return detected_boroughs, detected_neighborhoods


def retrieve_top_k_with_location_boost(
    query_vector: list[float],
    index: list[tuple[dict, list[float]]],
    k: int,
    target_boroughs: set[str],
    borough_boost: float,
) -> list[tuple[dict, float, float]]:
    """Retrieve top-k using base cosine similarity plus optional borough boost.

    Returns tuples of:
    - restaurant dict
    - final boosted score
    - base cosine score
    """
    scored = []
    for restaurant, emb in index:
        base_score = vectorizer.cosine_similarity(query_vector, emb)
        final_score = base_score

        borough = restaurant.get("borough")
        if target_boroughs and borough in target_boroughs:
            final_score += borough_boost

        scored.append((restaurant, final_score, base_score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]


def run_query_search(
    query: str,
    restaurants_path: Path = DEFAULT_RESTAURANTS_PATH,
    location_dict_path: Path = DEFAULT_LOCATION_DICT_PATH,
    top_k: int = 10,
    location_mode: str = "boost",
    borough_boost: float = 0.10,
) -> dict:
    """Run location-aware query retrieval and return results and diagnostics."""
    with restaurants_path.open("r", encoding="utf-8") as file:
        restaurants = json.load(file)

    neighborhood_to_borough = load_neighborhood_mapping(location_dict_path)
    target_boroughs, detected_neighborhoods = detect_location_intent(query, neighborhood_to_borough)

    query_vector = vectorizer.embed_query(query)
    index = vectorizer.build_restaurant_index(restaurants)

    if location_mode == "boost":
        ranked = retrieve_top_k_with_location_boost(
            query_vector=query_vector,
            index=index,
            k=top_k,
            target_boroughs=target_boroughs,
            borough_boost=borough_boost,
        )
    else:
        base = vectorizer.retrieve_top_k(query_vector, index, k=top_k)
        ranked = [(restaurant, score, score) for restaurant, score in base]

    return {
        "query": query,
        "location_mode": location_mode,
        "detected_neighborhoods": sorted(detected_neighborhoods),
        "target_boroughs": sorted(target_boroughs),
        "results": ranked,
    }


def _format_categories(categories) -> str:
    """Format category field for concise printing."""
    if isinstance(categories, list):
        return ", ".join(categories[:4])
    return str(categories)


def print_results(payload: dict, top_k: int) -> None:
    """Print ranked results and location diagnostics."""
    print("Task: location-aware query search")
    print(f"Query: {payload['query']}")
    print(f"Location mode: {payload['location_mode']}")
    print(
        "Detected neighborhoods: "
        f"{payload['detected_neighborhoods'] if payload['detected_neighborhoods'] else 'None'}"
    )
    print(
        "Target boroughs: "
        f"{payload['target_boroughs'] if payload['target_boroughs'] else 'None'}"
    )

    print(f"Top {top_k} matches:")
    results = payload["results"]
    if not results:
        print("No results found.")
        return

    for i, (restaurant, score, base_score) in enumerate(results, start=1):
        print(
            f"{i}. score={score:.4f} (base={base_score:.4f}) | "
            f"name={restaurant.get('name')} | "
            f"borough={restaurant.get('borough')} | "
            f"categories={_format_categories(restaurant.get('categories', []))} | "
            f"business_id={restaurant.get('business_id')}"
        )


def main() -> None:
    """CLI entry point for location-aware search over raw restaurant JSON."""
    parser = argparse.ArgumentParser(
        description="Location-aware semantic search over restaurants_with_google_reviews_final.json",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Natural-language user query",
    )
    parser.add_argument(
        "--restaurants-json",
        type=Path,
        default=DEFAULT_RESTAURANTS_PATH,
        help="Path to restaurant JSON with document and google_reviews fields",
    )
    parser.add_argument(
        "--location-dict",
        type=Path,
        default=DEFAULT_LOCATION_DICT_PATH,
        help="Path to neighborhood->borough mapping JSON",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top matches to return",
    )
    parser.add_argument(
        "--location-mode",
        type=str,
        choices=["off", "boost"],
        default="boost",
        help="Whether to apply borough boost based on detected location intent",
    )
    parser.add_argument(
        "--borough-boost",
        type=float,
        default=0.10,
        help="Score bonus for matches in detected target boroughs",
    )
    args = parser.parse_args()

    payload = run_query_search(
        query=args.query,
        restaurants_path=args.restaurants_json,
        location_dict_path=args.location_dict,
        top_k=args.top_k,
        location_mode=args.location_mode,
        borough_boost=args.borough_boost,
    )
    print_results(payload, args.top_k)


if __name__ == "__main__":
    main()
