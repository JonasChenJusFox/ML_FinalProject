"""
frontend/location_utils.py
Owner: Jonas Chen

Responsibilities:
- Normalizes borough and area labels for frontend display and filtering
- Provides lightweight NYC area lookup for current-origin labeling
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

_BOROUGH_NAMES = set(_BOROUGH_ALIASES.values())
_SEARCH_TEXT_RE = re.compile(r"[^a-z0-9]+")
_AREA_ALIASES = {
    "long island city": "Long Island City",
}

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

ZIPCODE_LOCATIONS: dict[str, dict[str, Any]] = {
    "10004": {"label": "Battery Park / Financial District", "lat": 40.7026, "lon": -74.0129},
    "10005": {"label": "Financial District / Wall Street", "lat": 40.7060, "lon": -74.0088},
    "10006": {"label": "World Trade Center / Financial District", "lat": 40.7096, "lon": -74.0134},
    "10007": {"label": "Tribeca / Civic Center", "lat": 40.7130, "lon": -74.0086},
    "10001": {"label": "Chelsea / Midtown South", "lat": 40.7506, "lon": -73.9972},
    "10002": {"label": "Lower East Side", "lat": 40.7174, "lon": -73.9890},
    "10003": {"label": "NYU / East Village", "lat": 40.7318, "lon": -73.9892},
    "10009": {"label": "Alphabet City / East Village", "lat": 40.7272, "lon": -73.9786},
    "10010": {"label": "Gramercy / Flatiron", "lat": 40.7385, "lon": -73.9826},
    "10011": {"label": "Chelsea / West Village", "lat": 40.7420, "lon": -74.0008},
    "10012": {"label": "SoHo / Greenwich Village", "lat": 40.7253, "lon": -73.9986},
    "10013": {"label": "SoHo / Chinatown / Tribeca", "lat": 40.7205, "lon": -74.0047},
    "10014": {"label": "West Village", "lat": 40.7364, "lon": -74.0055},
    "10016": {"label": "Murray Hill / Kips Bay", "lat": 40.7467, "lon": -73.9785},
    "10017": {"label": "Midtown East / Grand Central", "lat": 40.7527, "lon": -73.9725},
    "10018": {"label": "Times Square / Garment District", "lat": 40.7546, "lon": -73.9926},
    "10019": {"label": "Midtown West", "lat": 40.7656, "lon": -73.9854},
    "10020": {"label": "Rockefeller Center / Midtown", "lat": 40.7587, "lon": -73.9801},
    "10021": {"label": "Upper East Side", "lat": 40.7684, "lon": -73.9580},
    "10022": {"label": "Midtown East", "lat": 40.7589, "lon": -73.9680},
    "10023": {"label": "Upper West Side / Lincoln Center", "lat": 40.7774, "lon": -73.9829},
    "10024": {"label": "Upper West Side", "lat": 40.7867, "lon": -73.9760},
    "10025": {"label": "Morningside Heights", "lat": 40.7980, "lon": -73.9686},
    "10026": {"label": "Central Harlem", "lat": 40.8017, "lon": -73.9544},
    "10027": {"label": "Morningside Heights / Harlem", "lat": 40.8116, "lon": -73.9552},
    "10028": {"label": "Upper East Side", "lat": 40.7764, "lon": -73.9537},
    "10029": {"label": "East Harlem", "lat": 40.7916, "lon": -73.9444},
    "10030": {"label": "Harlem", "lat": 40.8185, "lon": -73.9431},
    "10031": {"label": "Hamilton Heights", "lat": 40.8252, "lon": -73.9493},
    "10032": {"label": "Washington Heights", "lat": 40.8389, "lon": -73.9422},
    "10033": {"label": "Washington Heights", "lat": 40.8504, "lon": -73.9357},
    "10034": {"label": "Inwood / Marble Hill", "lat": 40.8677, "lon": -73.9212},
    "10035": {"label": "East Harlem", "lat": 40.8011, "lon": -73.9369},
    "10036": {"label": "Times Square / Hell's Kitchen", "lat": 40.7598, "lon": -73.9918},
    "10037": {"label": "Harlem", "lat": 40.8135, "lon": -73.9371},
    "10038": {"label": "Financial District / Seaport", "lat": 40.7099, "lon": -74.0023},
    "10039": {"label": "Hamilton Heights / Harlem", "lat": 40.8267, "lon": -73.9386},
    "10040": {"label": "Inwood", "lat": 40.8587, "lon": -73.9287},
    "10451": {"label": "Bronx", "lat": 40.8172, "lon": -73.9223},
    "10301": {"label": "Staten Island", "lat": 40.6437, "lon": -74.0736},
    "11101": {"label": "Long Island City", "lat": 40.7447, "lon": -73.9485},
    "11102": {"label": "Astoria", "lat": 40.7717, "lon": -73.9277},
    "11103": {"label": "Astoria", "lat": 40.7621, "lon": -73.9118},
    "11104": {"label": "Sunnyside", "lat": 40.7449, "lon": -73.9196},
    "11105": {"label": "Astoria / Ditmars", "lat": 40.7796, "lon": -73.9080},
    "11106": {"label": "Astoria", "lat": 40.7617, "lon": -73.9295},
    "11205": {"label": "Fort Greene / Clinton Hill", "lat": 40.6949, "lon": -73.9661},
    "11206": {"label": "East Williamsburg / Bushwick", "lat": 40.7011, "lon": -73.9427},
    "11201": {"label": "Downtown Brooklyn", "lat": 40.6943, "lon": -73.9918},
    "11211": {"label": "Williamsburg", "lat": 40.7143, "lon": -73.9571},
    "11215": {"label": "Park Slope", "lat": 40.6671, "lon": -73.9852},
    "11217": {"label": "Prospect Heights", "lat": 40.6819, "lon": -73.9762},
    "11218": {"label": "Kensington / Windsor Terrace", "lat": 40.6451, "lon": -73.9778},
    "11221": {"label": "Bed-Stuy / Bushwick", "lat": 40.6915, "lon": -73.9275},
    "11222": {"label": "Greenpoint", "lat": 40.7280, "lon": -73.9515},
    "11231": {"label": "Carroll Gardens / Red Hook", "lat": 40.6776, "lon": -74.0014},
    "11238": {"label": "Clinton Hill / Prospect Heights", "lat": 40.6812, "lon": -73.9647},
    "11249": {"label": "Williamsburg Waterfront", "lat": 40.7188, "lon": -73.9582},
    "11354": {"label": "Flushing", "lat": 40.7675, "lon": -73.8271},
    "11355": {"label": "Flushing", "lat": 40.7492, "lon": -73.8196},
    "11368": {"label": "Corona", "lat": 40.7498, "lon": -73.8528},
    "11372": {"label": "Jackson Heights", "lat": 40.7505, "lon": -73.8831},
    "11373": {"label": "Elmhurst", "lat": 40.7386, "lon": -73.8786},
    "11375": {"label": "Forest Hills", "lat": 40.7214, "lon": -73.8442},
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


_AREA_BY_NORMALIZED_NAME: dict[str, dict[str, Any]] = {}
for _area in SEARCH_AREAS:
    for _candidate in [_area["name"], *_area.get("aliases", [])]:
        _normalized_candidate = _normalize_search_text(_candidate)
        if _normalized_candidate:
            _AREA_BY_NORMALIZED_NAME[_normalized_candidate] = _area


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
