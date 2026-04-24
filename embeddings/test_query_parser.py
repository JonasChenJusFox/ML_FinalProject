"""Runnable smoke tests for embeddings.query_parser.

Usage:
    python embeddings/test_query_parser.py
    python embeddings/test_query_parser.py --query "cheap vegan brunch near me in astoria"
    python embeddings/test_query_parser.py --location-file config/neighborhood_to_borough_nyc.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "query_parser.py"
_SPEC = importlib.util.spec_from_file_location("query_parser", MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load query parser module from {MODULE_PATH}")
query_parser = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(query_parser)

DEFAULT_QUERIES = [
    "budget-friendly vegetarian lunch near me in astoria",
    "cozy romantic dinner in west village",
    "family-friendly brunch within 25 minutes",
    "quick bite in midtown under 15 min",
    "halal gluten-free dinner within 2 miles",
    "luxury omakase tasting menu in soho",
    "any budget casual spot close by",
    "quiet business lunch within 5 km",
    "late-night drinks and dessert in lower east side",
    "vegan breakfast around me",
]


def _load_location_keywords(path_value: str | None) -> dict | None:
    if not path_value:
        return None

    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"Location file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Location file must contain a JSON object/dictionary.")

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run query parser smoke tests.")
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Custom query to parse. You can pass this flag multiple times.",
    )
    parser.add_argument(
        "--location-file",
        default=None,
        help="Optional JSON file path for location keyword matching.",
    )

    args = parser.parse_args()
    location_keywords = _load_location_keywords(args.location_file)
    if location_keywords is not None:
        query_parser.LOCATION_KEYWORDS = location_keywords

    queries = args.query if args.query else DEFAULT_QUERIES

    for index, query in enumerate(queries, start=1):
        result = query_parser.parse_query(query=query)
        print(f"[{index}] Query: {query}")
        print(json.dumps(result, indent=2, ensure_ascii=True))
        print("-" * 60)


if __name__ == "__main__":
    main()
