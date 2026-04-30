"""Parse raw search text into lightweight structured query signals.

This module extracts deterministic keyword hints for price, dietary needs,
location, occasion, and meal context, then produces a cleaned query string for
embedding.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from embeddings.location_lookup import NEIGHBORHOOD_CENTROIDS, resolve_location_coordinate

NYU_LAT = 40.7295
NYU_LON = -73.9965

PRICE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cheap": (
        "cheap",
        "affordable",
        "budget",
        "budget-friendly",
        "budget friendly",
        "inexpensive",
        "low cost",
        "low-cost",
        "economical",
        "value",
        "good value",
        "great value",
        "cost effective",
        "cost-effective",
        "wallet friendly",
        "wallet-friendly",
        "student budget",
        "on a budget",
        "not expensive",
        "not too expensive",
        "casual pricing",
        "dollar",
        "$",
    ),
    "moderate": (
        "moderate",
        "mid-range",
        "mid range",
        "middle range",
        "medium price",
        "medium-priced",
        "reasonably priced",
        "reasonable",
        "fair price",
        "fairly priced",
        "not too pricey",
        "not too cheap",
        "average price",
        "standard price",
        "$$",
    ),
    "expensive": (
        "expensive",
        "pricey",
        "upscale",
        "fancy",
        "fine dining",
        "splurge",
        "high priced",
        "high-priced",
        "costly",
        "premium price",
        "premium-priced",
        "special occasion",
        "$$$",
    ),
    "luxury": (
        "luxury",
        "luxurious",
        "ultra luxury",
        "top tier",
        "top-tier",
        "elite",
        "exclusive",
        "white tablecloth",
        "chef's tasting",
        "chefs tasting",
        "tasting menu",
        "degustation",
        "omakase",
        "michelin star",
        "michelin-star",
        "michelin starred",
        "high-end",
        "high end",
        "premium",
        "michelin",
        "$$$$",
    ),
    "unknown": (
        "unknown",
        "any price",
        "any budget",
        "any cost",
        "no price preference",
        "no preference",
        "dont care about price",
        "don't care about price",
        "price doesnt matter",
        "price doesn't matter",
        "whatever price",
    ),
}

DIETARY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "vegan": (
        "vegan",
        "plant based",
        "plant-based",
        "strict vegetarian",
        "vegan-friendly",
        "vegan friendly",
        "no animal products",
        "dairy free vegan",
    ),
    "vegetarian": (
        "vegetarian",
        "veg",
        "meatless",
        "lacto vegetarian",
        "ovo vegetarian",
        "vegetarian-friendly",
        "vegetarian friendly",
    ),
    "halal": (
        "halal",
        "halal-friendly",
        "halal friendly",
        "zabiha",
        "zabihah",
        "dhabiha",
    ),
    "kosher": (
        "kosher",
        "kosher-style",
        "kosher style",
        "glatt kosher",
        "certified kosher",
    ),
    "gluten-free": (
        "gluten-free",
        "gluten free",
        "glutenfree",
        "gf",
        "celiac friendly",
        "celiac-safe",
        "celiac safe",
        "no gluten",
        "without gluten",
        "wheat free",
        "wheat-free",
    ),
}

OCCASION_VIBE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "date_night": ("date night", "date-night", "romantic date", "couples night"),
    "romantic": ("romantic", "intimate", "cozy date", "candlelit"),
    "quick_bite": (
        "quick bite",
        "quick-bite",
        "quick meal",
        "grab and go",
        "grab-and-go",
        "fast",
        "in a hurry",
    ),
    "casual": ("casual", "laid back", "laid-back", "easygoing", "chill"),
    "cozy": ("cozy", "cozy vibes", "homey", "warm atmosphere"),
    "quiet": ("quiet", "peaceful", "not noisy", "low noise", "calm"),
    "lively": (
        "lively",
        "vibrant",
        "buzzing",
        "energetic",
        "party vibe",
        "fun atmosphere",
    ),
    "group_friendly": (
        "large group",
        "group friendly",
        "group-friendly",
        "big table",
        "for a group",
    ),
    "family_friendly": (
        "family friendly",
        "family-friendly",
        "kid friendly",
        "kid-friendly",
        "with kids",
        "children",
    ),
    "business_meal": (
        "business dinner",
        "business lunch",
        "client dinner",
        "work dinner",
        "professional setting",
    ),
    "celebration": (
        "celebration",
        "birthday",
        "anniversary",
        "special occasion",
        "graduation",
        "party",
    ),
    "spicy": ("spicy", "hot", "kick"),
}

MEAL_CONTEXT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "breakfast": ("breakfast", "morning meal", "early morning"),
    "brunch": ("brunch", "bottomless brunch", "weekend brunch"),
    "lunch": ("lunch", "midday meal", "work lunch"),
    "dinner": ("dinner", "supper", "evening meal"),
    "late_night": (
        "late night",
        "late-night",
        "open late",
        "after midnight",
        "night owl",
    ),
    "dessert": ("dessert", "sweet", "sweets", "after dinner dessert"),
    "drinks": ("drinks", "cocktails", "wine", "bar", "happy hour"),
}

CUISINE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ramen": ("ramen",),
    "chinese": ("chinese", "chinese food"),
    "sushi": ("sushi",),
    "japanese": ("japanese", "japanese food"),
    "thai": ("thai", "thai food"),
    "korean": ("korean", "korean food"),
    "indian": ("indian", "indian food"),
    "mexican": ("mexican", "mexican food", "tacos", "taco", "burrito"),
    "italian": ("italian", "italian food", "pasta", "pizza"),
    "pizza": ("pizza",),
    "dessert": ("dessert", "desserts", "bakery", "pastry", "pastries", "cake"),
    "brunch": ("brunch",),
    "coffee": ("coffee", "cafe", "espresso"),
    "noodles": ("noodles", "noodle"),
    "burger": ("burger", "burgers"),
    "salad": ("salad", "salads"),
    "bagels": ("bagels", "bagel"),
}

DISTANCE_NEARBY_KEYWORDS: tuple[str, ...] = (
    "near me",
    "nearby",
    "close by",
    "closeby",
    "close to me",
    "around me",
    "walking distance",
    "walkable",
    "not far",
)

GENERIC_FILLER_WORDS: tuple[str, ...] = (
    "near",
    "in",
    "at",
    "around",
    "within",
    "under",
    "over",
    "about",
    "for",
    "by",
)

SPECIAL_LOCATION_KEYWORDS: dict[str, str] = {
    "nyu": "NYU",
    "new york university": "NYU",
    "campus": "NYU",
    "washington square": "NYU",
    "washington square park": "NYU",
    "brooklyn": "Brooklyn",
    "manhattan": "Manhattan",
    "queens": "Queens",
    "bronx": "Bronx",
    "staten island": "Staten_Island",
}

BOROUGH_CENTROIDS: dict[str, tuple[float, float]] = {
    "Brooklyn": (40.6782, -73.9442),
    "Manhattan": (40.7831, -73.9712),
    "Queens": (40.7282, -73.7949),
    "Bronx": (40.8448, -73.8648),
    "Staten_Island": (40.5795, -74.1502),
}


def _load_location_keyword_map() -> dict:
    """Load nyu_location_keyword_map for quick location keyword lookups."""
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "data" / "nyc_location_keyword_map.json"

    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


LOCATION_KEYWORD_MAP: dict = _load_location_keyword_map()


def _normalize_text(value: str) -> str:
    """Normalize free text for resilient keyword matching."""
    lowered = str(value or "").lower()
    lowered = lowered.replace("-", " ")
    lowered = re.sub(r"[^a-z0-9$\s]", " ", lowered)
    return " ".join(lowered.split())


def _contains_keyword(text: str, keyword: str) -> bool:
    """Return True when a keyword-like phrase appears in the text."""
    phrase = f" {_normalize_text(keyword)} "
    return phrase in f" {text} "


def _extract_price_label(normalized_query: str, raw_query: str) -> str | None:
    """Extract a dataset-aligned textual price bucket from query keywords."""
    under_amount = re.search(r"\b(?:under|below|less than)\s*\$?\s*(\d{1,3})\b", raw_query)
    if under_amount and int(under_amount.group(1)) <= 20:
        return "cheap"

    if "$$$$" in raw_query:
        return "luxury"
    if "$$$" in raw_query:
        return "expensive"
    if "$$" in raw_query:
        return "moderate"
    if "$" in raw_query:
        return "cheap"

    price_order = ("unknown", "luxury", "expensive", "moderate", "cheap")
    for label in price_order:
        for keyword in PRICE_KEYWORDS[label]:
            if _contains_keyword(normalized_query, keyword):
                return label
    return None


def _extract_dietary(normalized_query: str) -> list[str]:
    """Extract all supported dietary markers from a query."""
    matches: list[str] = []
    for canonical, aliases in DIETARY_KEYWORDS.items():
        for alias in aliases:
            if _contains_keyword(normalized_query, alias):
                if canonical not in matches:
                    matches.append(canonical)
                break
    return matches


def _extract_tagged_matches(
    normalized_query: str,
    mapping: dict[str, tuple[str, ...]],
) -> list[str]:
    """Extract canonical tags for any alias present in the query."""
    matches: list[str] = []
    for canonical, aliases in mapping.items():
        for alias in aliases:
            if _contains_keyword(normalized_query, alias):
                matches.append(canonical)
                break
    return matches


def _extract_distance_time_intent(
    normalized_query: str,
    raw_query: str,
    location: str | None = None,
) -> dict[str, Any]:
    """Extract proximity and travel-time signals from text."""
    near_me = any(_contains_keyword(normalized_query, alias) for alias in DISTANCE_NEARBY_KEYWORDS)

    lower_query = raw_query.lower()
    minute_matches = re.findall(r"\b(\d{1,3})\s*(?:min|mins|minute|minutes)\b", lower_query)
    km_matches = re.findall(r"\b(\d{1,3}(?:\.\d+)?)\s*(?:km|kilometer|kilometers)\b", lower_query)
    mile_matches = re.findall(r"\b(\d{1,3}(?:\.\d+)?)\s*(?:mi|mile|miles)\b", lower_query)

    max_minutes = min(int(value) for value in minute_matches) if minute_matches else None

    km_values: list[float] = []
    if km_matches:
        km_values.extend(float(value) for value in km_matches)
    if mile_matches:
        km_values.extend(float(value) * 1.60934 for value in mile_matches)
    max_km = min(km_values) if km_values else None

    return {
        "near_me": near_me,
        "max_minutes": max_minutes,
        "max_km": max_km,
    }


def _extract_location(normalized_query: str, location_keywords: dict | None) -> str | None:
    """Extract location using query parser's LOCATION_KEYWORD_MAP.
    
    This maps keywords/acronyms to neighborhood names (e.g., "NYU" -> "Greenwich Village").
    """
    # Check special hardcoded mappings first
    for alias, special in SPECIAL_LOCATION_KEYWORDS.items():
        if _contains_keyword(normalized_query, alias):
            return special

    # Direct zipcode support for queries like "near 10012".
    zipcode_match = re.search(r"\b\d{5}\b", normalized_query)
    if zipcode_match:
        return zipcode_match.group(0)

    if not location_keywords:
        return None

    best_match: tuple[int, str] | None = None

    # Try to match keywords from the map
    for keyword, neighborhood in location_keywords.items():
        keyword_text = str(keyword).strip()
        if not keyword_text:
            continue

        # Exact match on normalized keyword
        keyword_norm = _normalize_text(keyword_text)
        if keyword_norm and _contains_keyword(normalized_query, keyword_norm):
            score = len(keyword_norm)
            if best_match is None or score > best_match[0]:
                best_match = (score, str(neighborhood).strip())

    return best_match[1] if best_match else None


def _build_location_signal(label: str | None) -> dict[str, Any] | None:
    if not label:
        return None

    if label == "NYU":
        return {"label": "NYU", "lat": NYU_LAT, "lon": NYU_LON}

    if label in BOROUGH_CENTROIDS:
        lat, lon = BOROUGH_CENTROIDS[label]
        return {"label": label, "lat": lat, "lon": lon}

    coords = resolve_location_coordinate(label)
    if not coords:
        return {"label": label, "lat": None, "lon": None}

    lat, lon = coords
    return {"label": label, "lat": float(lat), "lon": float(lon)}


def _primary_meal_type(meal_context: list[str]) -> str | None:
    preferred_order = ("breakfast", "brunch", "lunch", "dinner", "late_night", "dessert", "drinks")
    for value in preferred_order:
        if value in meal_context:
            return value
    return meal_context[0] if meal_context else None


def _remove_phrases(text: str, phrases: list[str]) -> str:
    """Remove recognized phrases from a normalized query string."""
    working = f" {text} "
    for phrase in sorted({item for item in phrases if item}, key=len, reverse=True):
        normalized_phrase = _normalize_text(phrase)
        if not normalized_phrase:
            continue
        working = working.replace(f" {normalized_phrase} ", " ")
    return " ".join(working.split())


_IN_NEAR_CAPTURE_BLACKLIST = frozenset(
    {
        "me",
        "my",
        "you",
        "us",
        "it",
        "here",
        "there",
        "this",
        "that",
        "tomorrow",
        "today",
        "now",
    }
)

# Dataset uses ``Staten Island`` (spaced); keep aligned with ``restaurants.json``.
_BOROUGH_FROM_IN_NEAR_PHRASE: dict[str, str] = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "staten island": "Staten Island",
    "staten_island": "Staten Island",
}

# Walking-distance scale: keep results inside the named block / hood.
IN_NEAR_NEIGHBORHOOD_RADIUS_KM = 1.6


def _trim_in_near_tail(phrase: str) -> str:
    """Drop trailing conjunctive / filler clauses after the place token."""
    text = phrase.strip().strip("'\"")
    if not text:
        return ""
    for splitter in (
        r"\s+and\s+",
        r"\s+or\s+",
        r"\s+with\s+",
        r"\s+without\s+",
        r"\s+for\s+",
        r"\s+from\s+",
    ):
        parts = re.split(splitter, text, maxsplit=1, flags=re.IGNORECASE)
        text = parts[0].strip()
    return text


def _strip_leading_articles(phrase: str) -> str:
    text = phrase.strip()
    lowered = text.lower()
    for art in ("the ", "a ", "an "):
        if lowered.startswith(art):
            text = text[len(art) :].lstrip()
            lowered = text.lower()
    return text


def _borough_from_in_near_phrase(phrase: str) -> str | None:
    normalized = phrase.strip().lower().replace("_", " ")
    if not normalized:
        return None
    return _BOROUGH_FROM_IN_NEAR_PHRASE.get(normalized)


def _resolve_neighborhood_centroid(phrase: str) -> tuple[str, float, float] | None:
    """Return ``(label, lat, lon)`` when the phrase resolves to a mapped or known hood."""
    cleaned = _strip_leading_articles(_trim_in_near_tail(phrase))
    if len(cleaned) < 2:
        return None

    cleaned_lower = cleaned.lower()
    for alias, label in sorted(SPECIAL_LOCATION_KEYWORDS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if cleaned_lower == alias.lower():
            sig = _build_location_signal(label)
            if sig and sig.get("lat") is not None and sig.get("lon") is not None:
                return (str(label), float(sig["lat"]), float(sig["lon"]))

    for keyword, neighborhood in sorted(
        LOCATION_KEYWORD_MAP.items(),
        key=lambda kv: len(str(kv[0])),
        reverse=True,
    ):
        kw = str(keyword).strip()
        if not kw:
            continue
        if cleaned.lower() == kw.lower():
            hood = str(neighborhood).strip()
            coords = resolve_location_coordinate(hood)
            if coords:
                return (hood, float(coords[0]), float(coords[1]))
            continue

    coords_direct = resolve_location_coordinate(cleaned)
    if coords_direct:
        return (cleaned, float(coords_direct[0]), float(coords_direct[1]))

    cleaned_lower = cleaned.lower()
    for key in sorted(NEIGHBORHOOD_CENTROIDS.keys(), key=len, reverse=True):
        if cleaned_lower == key.lower():
            coord = NEIGHBORHOOD_CENTROIDS[key]
            if isinstance(coord, list) and len(coord) == 2:
                return (key, float(coord[0]), float(coord[1]))
    return None


def _extract_in_near_place_filter(raw_query: str) -> dict[str, Any] | None:
    """
    Detect ``in <place>`` / ``near <place>`` where ``<place>`` is a borough or a
    resolvable neighborhood. Used to hard-filter search results to that area.
    """
    raw = str(raw_query or "")
    if not raw.strip():
        return None

    matches = list(re.finditer(r"\b(in|near)\s+([^\n,.;!?]{2,60})", raw, flags=re.IGNORECASE))
    if not matches:
        return None

    for match in reversed(matches):
        raw_capture = match.group(2).strip()
        capture = _strip_leading_articles(_trim_in_near_tail(raw_capture))
        if not capture:
            continue
        first = capture.split()[0].lower() if capture.split() else ""
        if first in _IN_NEAR_CAPTURE_BLACKLIST or capture.lower() in _IN_NEAR_CAPTURE_BLACKLIST:
            continue

        borough = _borough_from_in_near_phrase(capture)
        if borough:
            return {"kind": "borough", "borough": borough, "phrase": capture}

        neighbor = _resolve_neighborhood_centroid(capture)
        if neighbor:
            label, lat, lon = neighbor
            return {
                "kind": "neighborhood",
                "label": label,
                "lat": lat,
                "lon": lon,
                "radius_km": IN_NEAR_NEIGHBORHOOD_RADIUS_KM,
                "phrase": capture,
            }
    return None


def minimal_clean_query(query: str) -> str:
    """Perform minimal cleaning: trim whitespace and normalize spacing.
    
    Do NOT remove semantic content like price, dietary, location, or meal context words.
    This output is suitable for embedding as it preserves the full query intent.
    """
    text = str(query or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_query(query: str) -> dict[str, Any]:
    """Parse a raw user query into structured keyword signals.
    
    Returns only structured signals (price, dietary, location, etc.) for filtering.
    The embedding should use the full original query, not a cleaned version.
    
    Location is extracted using LOCATION_KEYWORD_MAP which maps keywords/acronyms
    to neighborhood names (e.g., "NYU" -> "Greenwich Village").
    """
    raw_query = str(query or "")
    normalized_query = _normalize_text(raw_query)

    price = _extract_price_label(normalized_query, raw_query.lower())
    dietary = _extract_dietary(normalized_query)
    location_label = _extract_location(normalized_query, LOCATION_KEYWORD_MAP)
    location = _build_location_signal(location_label)
    cuisine = _extract_tagged_matches(normalized_query, CUISINE_KEYWORDS)
    occasion_vibe = _extract_tagged_matches(normalized_query, OCCASION_VIBE_KEYWORDS)
    meal_context = _extract_tagged_matches(normalized_query, MEAL_CONTEXT_KEYWORDS)
    in_near_place_filter = _extract_in_near_place_filter(raw_query)

    return {
        "price": price,
        "dietary": dietary,
        "location": location,
        "location_label": location_label,
        "cuisine": cuisine,
        "cuisines": cuisine,
        "vibe": occasion_vibe,
        "occasion_vibe": occasion_vibe,
        "meal_type": _primary_meal_type(meal_context),
        "meal_context": meal_context,
        "distance_time_intent": _extract_distance_time_intent(normalized_query, raw_query, location_label),
        "in_near_place_filter": in_near_place_filter,
    }
