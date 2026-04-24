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
    if not near_me and location and re.search(r"\bnear\b", normalized_query):
        near_me = True

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


def _remove_phrases(text: str, phrases: list[str]) -> str:
    """Remove recognized phrases from a normalized query string."""
    working = f" {text} "
    for phrase in sorted({item for item in phrases if item}, key=len, reverse=True):
        normalized_phrase = _normalize_text(phrase)
        if not normalized_phrase:
            continue
        working = working.replace(f" {normalized_phrase} ", " ")
    return " ".join(working.split())


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
    location = _extract_location(normalized_query, LOCATION_KEYWORD_MAP)

    return {
        "price": price,
        "dietary": dietary,
        "location": location,
        "occasion_vibe": _extract_tagged_matches(normalized_query, OCCASION_VIBE_KEYWORDS),
        "distance_time_intent": _extract_distance_time_intent(normalized_query, raw_query, location),
        "meal_context": _extract_tagged_matches(normalized_query, MEAL_CONTEXT_KEYWORDS),
    }
