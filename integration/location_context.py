"""
integration/location_context.py

Helpers for lightweight NYC area parsing and coordinate matching.
"""

from __future__ import annotations

import math
import re
from typing import Any

SEARCH_AREAS: list[dict[str, Any]] = [
    {
        "name": "Washington Square",
        "aliases": [
            "washington square park",
            "washington square",
            "washington sq",
            "wsq",
        ],
        "lat": 40.7308,
        "lon": -73.9973,
        "radius_km": 0.9,
        "borough": "Manhattan",
    },
    {
        "name": "Union Square",
        "aliases": ["union square"],
        "lat": 40.7359,
        "lon": -73.9911,
        "radius_km": 0.9,
        "borough": "Manhattan",
    },
    {
        "name": "Greenwich Village",
        "aliases": ["greenwich village", "the village"],
        "lat": 40.7336,
        "lon": -74.0027,
        "radius_km": 1.1,
        "borough": "Manhattan",
    },
    {
        "name": "West Village",
        "aliases": ["west village"],
        "lat": 40.7358,
        "lon": -74.0036,
        "radius_km": 1.1,
        "borough": "Manhattan",
    },
    {
        "name": "East Village",
        "aliases": ["east village", "ev"],
        "lat": 40.7265,
        "lon": -73.9815,
        "radius_km": 1.1,
        "borough": "Manhattan",
    },
    {
        "name": "SoHo",
        "aliases": ["soho"],
        "lat": 40.7233,
        "lon": -74.0030,
        "radius_km": 1.0,
        "borough": "Manhattan",
    },
    {
        "name": "Lower East Side",
        "aliases": ["lower east side", "les"],
        "lat": 40.7178,
        "lon": -73.9890,
        "radius_km": 1.2,
        "borough": "Manhattan",
    },
    {
        "name": "Chinatown",
        "aliases": ["chinatown"],
        "lat": 40.7158,
        "lon": -73.9970,
        "radius_km": 1.0,
        "borough": "Manhattan",
    },
    {
        "name": "Chelsea",
        "aliases": ["chelsea"],
        "lat": 40.7465,
        "lon": -74.0014,
        "radius_km": 1.2,
        "borough": "Manhattan",
    },
    {
        "name": "Koreatown",
        "aliases": ["koreatown", "ktown", "k-town"],
        "lat": 40.7478,
        "lon": -73.9861,
        "radius_km": 0.7,
        "borough": "Manhattan",
    },
    {
        "name": "Times Square",
        "aliases": ["times square"],
        "lat": 40.7580,
        "lon": -73.9855,
        "radius_km": 0.8,
        "borough": "Manhattan",
    },
    {
        "name": "Financial District",
        "aliases": ["financial district", "fidi"],
        "lat": 40.7075,
        "lon": -74.0113,
        "radius_km": 1.0,
        "borough": "Manhattan",
    },
    {
        "name": "Williamsburg",
        "aliases": ["williamsburg"],
        "lat": 40.7180,
        "lon": -73.9570,
        "radius_km": 1.5,
        "borough": "Brooklyn",
    },
    {
        "name": "DUMBO",
        "aliases": ["dumbo"],
        "lat": 40.7033,
        "lon": -73.9881,
        "radius_km": 0.9,
        "borough": "Brooklyn",
    },
    {
        "name": "Long Island City",
        "aliases": ["long island city", "lic"],
        "lat": 40.7447,
        "lon": -73.9485,
        "radius_km": 1.3,
        "borough": "Queens",
    },
    {
        "name": "Astoria",
        "aliases": ["astoria"],
        "lat": 40.7644,
        "lon": -73.9235,
        "radius_km": 1.5,
        "borough": "Queens",
    },
    {
        "name": "Flushing",
        "aliases": ["flushing"],
        "lat": 40.7590,
        "lon": -73.8303,
        "radius_km": 1.4,
        "borough": "Queens",
    },
]

LOCATION_FILLER_PATTERNS = [
    r"\bnear\b",
    r"\bnearby\b",
    r"\baround\b",
    r"\bclose to\b",
    r"\bin\b",
    r"\bat\b",
    r"\bby\b",
    r"\barea\b",
    r"\bfood\b",
    r"\bfoods\b",
    r"\brestaurant\b",
    r"\brestaurants\b",
    r"\bdining\b",
    r"\beats\b",
    r"\bplace to eat\b",
    r"\bplaces to eat\b",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _cleanup_area_query(value: str) -> str:
    cleaned = _normalize_text(value)
    for pattern in LOCATION_FILLER_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\s,./_-]+", " ", cleaned).strip()
    return cleaned


def extract_search_area(query: str) -> tuple[str, dict[str, Any] | None]:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return "", None

    alias_index: list[tuple[str, dict[str, Any]]] = []
    for area in SEARCH_AREAS:
        for alias in area.get("aliases", []):
            alias_index.append((str(alias).lower(), area))

    for alias, area in sorted(alias_index, key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, normalized_query):
            cleaned_query = re.sub(pattern, " ", normalized_query, count=1)
            return _cleanup_area_query(cleaned_query), area

    return normalized_query, None


def find_nearest_search_area(
    latitude: float | None,
    longitude: float | None,
    *,
    max_distance_km: float = 1.2,
) -> dict[str, Any] | None:
    if latitude is None or longitude is None:
        return None

    nearest_area = None
    nearest_distance = None

    for area in SEARCH_AREAS:
        distance = haversine_km(
            float(latitude),
            float(longitude),
            float(area["lat"]),
            float(area["lon"]),
        )
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_area = area

    if nearest_area is None or nearest_distance is None or nearest_distance > max_distance_km:
        return None

    return nearest_area


def annotate_area_distance(
    restaurants: list[dict[str, Any]],
    area: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if area is None:
        return [dict(item) for item in restaurants]

    annotated: list[dict[str, Any]] = []
    area_lat = float(area["lat"])
    area_lon = float(area["lon"])

    for restaurant in restaurants:
        item = dict(restaurant)
        latitude = item.get("latitude")
        longitude = item.get("longitude")
        if latitude is None or longitude is None:
            item["query_area_distance_km"] = None
        else:
            item["query_area_distance_km"] = haversine_km(
                float(latitude),
                float(longitude),
                area_lat,
                area_lon,
            )
        annotated.append(item)

    return annotated


def filter_restaurants_by_area(
    restaurants: list[dict[str, Any]],
    area: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if area is None:
        return list(restaurants)

    max_distance_km = float(area.get("radius_km", 1.0))
    filtered: list[dict[str, Any]] = []
    for item in annotate_area_distance(restaurants, area):
        distance = item.get("query_area_distance_km")
        if distance is None:
            continue
        if float(distance) <= max_distance_km:
            filtered.append(item)

    return filtered


def is_generic_area_query(query: str) -> bool:
    return _cleanup_area_query(query) == ""
