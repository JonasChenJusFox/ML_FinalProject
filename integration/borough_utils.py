"""
integration/borough_utils.py

Helpers for normalizing NYC borough labels from noisy restaurant records.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NEIGHBORHOOD_BOROUGH_PATH = REPO_ROOT / "config" / "neighborhood_to_borough_nyc.json"

_BOROUGH_ALIASES = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "the bronx": "Bronx",
    "staten island": "Staten Island",
    "staten_island": "Staten Island",
}

_AREA_ALIASES = {
    "long island city": "Long Island City",
}

try:
    _NEIGHBORHOOD_TO_BOROUGH = json.loads(NEIGHBORHOOD_BOROUGH_PATH.read_text())
except Exception:
    _NEIGHBORHOOD_TO_BOROUGH = {}

_BOROUGH_NAMES = set(_BOROUGH_ALIASES.values())
_SEARCH_TEXT_RE = re.compile(r"[^a-z0-9]+")


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_key(value: object) -> str:
    return _clean_text(value).lower().replace("_", " ")


def _normalize_search_text(value: object) -> str:
    normalized = _normalize_key(value)
    return _SEARCH_TEXT_RE.sub(" ", normalized).strip()


def canonicalize_borough(value: object) -> str:
    normalized = _normalize_key(value)
    if not normalized:
        return ""
    return _BOROUGH_ALIASES.get(normalized, _clean_text(value))


def get_location_filter_options() -> list[str]:
    return [
        "Brooklyn",
        "Bronx",
        "Long Island City",
        "Manhattan",
        "Queens",
        "Staten Island",
    ]


_NORMALIZED_NEIGHBORHOOD_TO_BOROUGH = {
    _normalize_key(neighborhood): canonicalize_borough(borough)
    for neighborhood, borough in _NEIGHBORHOOD_TO_BOROUGH.items()
    if _normalize_key(neighborhood) and canonicalize_borough(borough) in _BOROUGH_NAMES
}

_SORTED_NEIGHBORHOOD_KEYS = sorted(
    _NORMALIZED_NEIGHBORHOOD_TO_BOROUGH.keys(),
    key=len,
    reverse=True,
)

_BOROUGH_ALIAS_SEARCH = {
    _normalize_search_text(alias): borough
    for alias, borough in _BOROUGH_ALIASES.items()
}


def _flatten_part(part: object) -> str:
    if isinstance(part, list):
        return " ".join(_clean_text(item) for item in part if _clean_text(item))
    return _clean_text(part)


@lru_cache(maxsize=16384)
def _infer_borough_cached(
    city: str,
    neighborhood: str,
    address: str,
    address1: str,
    address2: str,
    address3: str,
    display_address: str,
    borough: str,
) -> str:
    for raw_value in (city, neighborhood):
        normalized = _normalize_key(raw_value)
        if not normalized:
            continue

        mapped = _NORMALIZED_NEIGHBORHOOD_TO_BOROUGH.get(normalized)
        if mapped:
            return mapped

        candidate = _BOROUGH_ALIASES.get(normalized)
        if candidate:
            return candidate

    raw_borough = canonicalize_borough(borough)

    address_parts = [
        address,
        address1,
        address2,
        address3,
        display_address,
        city,
        neighborhood,
    ]
    haystack = _normalize_search_text(" ".join(part for part in address_parts if part))
    if haystack:
        padded_haystack = f" {haystack} "

        for alias, borough_name in _BOROUGH_ALIAS_SEARCH.items():
            if alias and f" {alias} " in padded_haystack:
                return borough_name

        for neighborhood_key in _SORTED_NEIGHBORHOOD_KEYS:
            if f" {neighborhood_key} " in padded_haystack:
                return _NORMALIZED_NEIGHBORHOOD_TO_BOROUGH[neighborhood_key]

    return raw_borough


def infer_borough(restaurant: dict) -> str:
    if not isinstance(restaurant, dict):
        return ""

    return _infer_borough_cached(
        _flatten_part(restaurant.get("city")),
        _flatten_part(restaurant.get("neighborhood")),
        _flatten_part(restaurant.get("address")),
        _flatten_part(restaurant.get("address1")),
        _flatten_part(restaurant.get("address2")),
        _flatten_part(restaurant.get("address3")),
        _flatten_part(restaurant.get("display_address")),
        _flatten_part(restaurant.get("borough")),
    )


def matches_location_filter(restaurant: dict, selection: object) -> bool:
    normalized_selection = _normalize_key(selection)
    if not normalized_selection or normalized_selection == "all":
        return True

    area_name = _AREA_ALIASES.get(normalized_selection)
    if area_name == "Long Island City":
        searchable_parts = [
            restaurant.get("city"),
            restaurant.get("neighborhood"),
            restaurant.get("address"),
            restaurant.get("address1"),
            restaurant.get("address2"),
            restaurant.get("address3"),
            restaurant.get("display_address"),
        ]
        haystack = _normalize_search_text(" ".join(_flatten_part(part) for part in searchable_parts if part))
        return " long island city " in f" {haystack} "

    return canonicalize_borough(infer_borough(restaurant)) == canonicalize_borough(selection)
