"""
frontend/location_utils.py
Owner: Jonas Chen

Responsibilities:
- Normalizes borough and area labels for frontend display and filtering
- Provides lightweight NYC area and ZIP lookup for current-origin labeling
- Keeps UI-facing location helpers separate from backend search code
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
NEIGHBORHOOD_BOROUGH_PATH = REPO_ROOT / "config" / "neighborhood_to_borough_nyc.json"
LOCATION_KEYWORD_MAP_PATH = REPO_ROOT / "data" / "nyc_location_keyword_map.json"
NEIGHBORHOOD_CENTROIDS_PATH = REPO_ROOT / "data" / "nyc_neighborhood_centroids.json"
ZIPCODE_CENTROIDS_PATH = REPO_ROOT / "data" / "nyc_zipcode_centroids.json"

NYU_LAT = 40.7295
NYU_LON = -73.9965

_BOROUGH_ALIASES = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "the bronx": "Bronx",
    "staten island": "Staten Island",
    "staten_island": "Staten Island",
}

try:
    _NEIGHBORHOOD_TO_BOROUGH = json.loads(NEIGHBORHOOD_BOROUGH_PATH.read_text())
except Exception:
    _NEIGHBORHOOD_TO_BOROUGH = {}

try:
    _LOCATION_KEYWORD_MAP = json.loads(LOCATION_KEYWORD_MAP_PATH.read_text())
except Exception:
    _LOCATION_KEYWORD_MAP = {}

try:
    _NEIGHBORHOOD_CENTROIDS = json.loads(NEIGHBORHOOD_CENTROIDS_PATH.read_text())
except Exception:
    _NEIGHBORHOOD_CENTROIDS = {}

try:
    _ZIPCODE_CENTROIDS = json.loads(ZIPCODE_CENTROIDS_PATH.read_text())
except Exception:
    _ZIPCODE_CENTROIDS = {}

_BOROUGH_NAMES = set(_BOROUGH_ALIASES.values())
_SEARCH_TEXT_RE = re.compile(r"[^a-z0-9]+")
_AREA_ALIASES = {
    "long island city": "Long Island City",
}

_CURATED_SEARCH_AREAS: list[dict[str, Any]] = [
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

_ZIPCODE_LABEL_OVERRIDES = {
    "10001": "Chelsea / Midtown South",
    "10002": "Lower East Side",
    "10003": "NYU / Washington Square / East Village",
    "10004": "Battery Park / Financial District",
    "10005": "Financial District / Wall Street",
    "10006": "World Trade Center / Financial District",
    "10007": "Tribeca / Civic Center",
    "10009": "Alphabet City / East Village",
    "10010": "Gramercy / Flatiron",
    "10011": "Chelsea / West Village",
    "10012": "SoHo / Greenwich Village",
    "10013": "SoHo / Chinatown / Tribeca",
    "10014": "West Village",
    "10016": "Murray Hill / Kips Bay",
    "10017": "Midtown East / Grand Central",
    "10018": "Times Square / Garment District",
    "10019": "Midtown West",
    "10020": "Rockefeller Center / Midtown",
    "10021": "Upper East Side",
    "10022": "Midtown East",
    "10023": "Upper West Side / Lincoln Center",
    "10024": "Upper West Side",
    "10025": "Morningside Heights",
    "10026": "Central Harlem",
    "10027": "Morningside Heights / Harlem",
    "10028": "Upper East Side",
    "10029": "East Harlem",
    "10030": "Harlem",
    "10031": "Hamilton Heights",
    "10032": "Washington Heights",
    "10033": "Washington Heights",
    "10034": "Inwood / Marble Hill",
    "10035": "East Harlem",
    "10036": "Times Square / Hell's Kitchen",
    "10037": "Harlem",
    "10038": "Financial District / Seaport",
    "10039": "Hamilton Heights / Harlem",
    "10040": "Inwood",
    "10301": "Staten Island",
    "10451": "Bronx",
    "11101": "Long Island City",
    "11102": "Astoria",
    "11103": "Astoria",
    "11104": "Sunnyside",
    "11105": "Astoria / Ditmars",
    "11106": "Astoria",
    "11201": "Downtown Brooklyn",
    "11205": "Fort Greene / Clinton Hill",
    "11206": "East Williamsburg / Bushwick",
    "11211": "Williamsburg",
    "11215": "Park Slope",
    "11217": "Prospect Heights",
    "11218": "Kensington / Windsor Terrace",
    "11221": "Bed-Stuy / Bushwick",
    "11222": "Greenpoint",
    "11231": "Carroll Gardens / Red Hook",
    "11238": "Clinton Hill / Prospect Heights",
    "11249": "Williamsburg Waterfront",
    "11354": "Flushing",
    "11355": "Flushing",
    "11368": "Corona",
    "11372": "Jackson Heights",
    "11373": "Elmhurst",
    "11375": "Forest Hills",
}

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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


def _default_radius_for_borough(borough: str) -> float:
    if borough == "Manhattan":
        return 1.0
    if borough in {"Brooklyn", "Queens"}:
        return 1.3
    return 1.5


_CURATED_AREA_LOOKUP = {
    _normalize_search_text(area["name"]): area
    for area in _CURATED_SEARCH_AREAS
}


def _build_search_areas() -> list[dict[str, Any]]:
    alias_map_by_area: dict[str, set[str]] = {}
    for raw_alias, raw_name in _LOCATION_KEYWORD_MAP.items():
        alias = _clean_text(raw_alias)
        canonical_name = _clean_text(raw_name)
        if alias and canonical_name:
            alias_map_by_area.setdefault(canonical_name, set()).add(alias)

    built: list[dict[str, Any]] = []
    for area in _CURATED_SEARCH_AREAS:
        merged_area = dict(area)
        merged_aliases = {
            _clean_text(alias)
            for alias in merged_area.get("aliases", [])
            if _clean_text(alias)
        }
        merged_aliases.update(alias_map_by_area.get(merged_area["name"], set()))
        merged_area["aliases"] = sorted(merged_aliases)
        built.append(merged_area)
    seen = set(_CURATED_AREA_LOOKUP.keys())

    for raw_name, coords in _NEIGHBORHOOD_CENTROIDS.items():
        name = _clean_text(raw_name)
        normalized_name = _normalize_search_text(name)
        if not name or normalized_name in seen:
            continue
        if not isinstance(coords, list) or len(coords) != 2:
            continue

        try:
            latitude = float(coords[0])
            longitude = float(coords[1])
        except (TypeError, ValueError):
            continue

        borough = canonicalize_borough(_NEIGHBORHOOD_TO_BOROUGH.get(name, ""))
        aliases = sorted(alias_map_by_area.get(name, set()))

        built.append(
            {
                "name": name,
                "aliases": aliases,
                "lat": latitude,
                "lon": longitude,
                "radius_km": _default_radius_for_borough(borough),
                "borough": borough,
            }
        )
        seen.add(normalized_name)

    return built


def _build_zipcode_locations() -> dict[str, dict[str, Any]]:
    built: dict[str, dict[str, Any]] = {}
    for raw_zipcode, coords in _ZIPCODE_CENTROIDS.items():
        zipcode = str(raw_zipcode).strip()
        if not zipcode:
            continue
        if not isinstance(coords, list) or len(coords) != 2:
            continue
        try:
            latitude = float(coords[0])
            longitude = float(coords[1])
        except (TypeError, ValueError):
            continue

        label = _ZIPCODE_LABEL_OVERRIDES.get(zipcode, f"ZIP {zipcode}")
        built[zipcode] = {
            "label": label,
            "lat": latitude,
            "lon": longitude,
        }
    return built


SEARCH_AREAS: list[dict[str, Any]] = _build_search_areas()
ZIPCODE_LOCATIONS: dict[str, dict[str, Any]] = _build_zipcode_locations()


_AREA_BY_NORMALIZED_NAME: dict[str, dict[str, Any]] = {}
for _area in SEARCH_AREAS:
    for _candidate in [_area["name"], *_area.get("aliases", [])]:
        _normalized_candidate = _normalize_search_text(_candidate)
        if _normalized_candidate:
            _AREA_BY_NORMALIZED_NAME[_normalized_candidate] = _area


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


def matches_location_filter(restaurant: dict, selected_location: object) -> bool:
    normalized = _normalize_key(selected_location)
    if not normalized or normalized == "all":
        return True

    search_area = _AREA_BY_NORMALIZED_NAME.get(_normalize_search_text(selected_location))
    if search_area:
        haystack_parts = [
            restaurant.get("location_search_text", ""),
            restaurant.get("borough", ""),
            restaurant.get("city", ""),
            restaurant.get("neighborhood", ""),
            restaurant.get("address", ""),
            restaurant.get("address1", ""),
            restaurant.get("address2", ""),
            restaurant.get("address3", ""),
            restaurant.get("display_address", []),
        ]
        haystack = _normalize_search_text(" ".join(_flatten_part(part) for part in haystack_parts))
        area_candidates = [search_area["name"], *search_area.get("aliases", [])]
        return any(_normalize_search_text(candidate) in haystack for candidate in area_candidates)

    canonical = canonicalize_borough(selected_location)
    inferred = canonicalize_borough(infer_borough(restaurant))
    if canonical and canonical in _BOROUGH_NAMES:
        return inferred == canonical

    if normalized in _AREA_ALIASES:
        target = _AREA_ALIASES[normalized]
        haystack_parts = [
            restaurant.get("location_search_text", ""),
            restaurant.get("borough", ""),
            restaurant.get("city", ""),
            restaurant.get("neighborhood", ""),
            restaurant.get("address", ""),
            restaurant.get("address1", ""),
            restaurant.get("address2", ""),
            restaurant.get("address3", ""),
            restaurant.get("display_address", []),
        ]
        haystack = _normalize_search_text(" ".join(_flatten_part(part) for part in haystack_parts))
        return normalized in haystack or _normalize_search_text(target) in haystack

    return inferred == canonicalize_borough(selected_location)


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


def get_supported_zipcode_options() -> list[str]:
    return sorted(ZIPCODE_LOCATIONS.keys())


def resolve_zipcode_location(zipcode: object) -> dict[str, Any] | None:
    normalized = str(zipcode or "").strip()
    if not normalized:
        return None
    return ZIPCODE_LOCATIONS.get(normalized)


def _build_area_location_result(area: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(area.get("name", "")).strip(),
        "lat": float(area["lat"]),
        "lon": float(area["lon"]),
        "area_label": str(area.get("name", "")).strip(),
    }


@lru_cache(maxsize=4096)
def resolve_area_location(query: object) -> dict[str, Any] | None:
    raw_query = _clean_text(query)
    normalized_query = _normalize_search_text(raw_query)
    if not normalized_query:
        return None

    exact_area = _AREA_BY_NORMALIZED_NAME.get(normalized_query)
    if exact_area:
        return _build_area_location_result(exact_area)

    zipcode_match = re.search(r"\b(\d{5})\b", raw_query)
    if zipcode_match:
        zipcode = zipcode_match.group(1)
        zipcode_location = resolve_zipcode_location(zipcode)
        if zipcode_location:
            return {
                "label": f"ZIP {zipcode}",
                "lat": float(zipcode_location["lat"]),
                "lon": float(zipcode_location["lon"]),
                "area_label": str(zipcode_location.get("label", "")).strip(),
            }

    best_area: dict[str, Any] | None = None
    best_score: tuple[int, int, int] | None = None

    for area in SEARCH_AREAS:
        candidates = [area["name"], *area.get("aliases", [])]
        for candidate in candidates:
            normalized_candidate = _normalize_search_text(candidate)
            if not normalized_candidate:
                continue
            if normalized_query not in normalized_candidate and normalized_candidate not in normalized_query:
                continue

            score = (
                0 if normalized_query == normalized_candidate else 1,
                abs(len(normalized_candidate) - len(normalized_query)),
                len(normalized_candidate),
            )
            if best_score is None or score < best_score:
                best_area = area
                best_score = score

    if best_area:
        return _build_area_location_result(best_area)

    return None
