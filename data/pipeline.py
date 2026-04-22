"""
data/pipeline.py
Owner: Yue

Responsibilities:
- Ingest restaurant data from Yelp Fusion API
- Clean and normalize fields
- Structure dataset for embedding and search
- Build user interaction history table (synthetic or real)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
RESTAURANTS_PATH = REPO_ROOT / "data" / "restaurants.json"
USER_INTERACTIONS_PATH = REPO_ROOT / "data" / "user_interactions.json"
SYNTHETIC_USER_PROFILES_PATH = REPO_ROOT / "data" / "synthetic_user_profiles.json"


def _optional_float(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_restaurants(source: str = "yelp_cache") -> list[dict]:
    """
    Load restaurant records from local cache or Yelp API.

    Args:
        source: One of 'yelp_cache', 'yelp_api', 'csv'

    Returns:
        List of restaurant dicts with normalized fields.

    Expected output schema per restaurant:
        {
            "business_id": str,
            "name": str,
            "image_url": str,
            "rating": float,
            "review_count": int,
            "price": str,          # "$" to "$$$$$"
            "categories": list[str],
            "latitude": float,
            "longitude": float,
            "address": str,
            "phone": str,
            "transactions": list[str],
            "url": str,
            "is_closed": bool,
            "neighborhood": str,
            "hours": dict,
            "attributes": dict,    # pet_friendly, kid_friendly, etc.
        }
    """
    if source.endswith(".json"):
        target_path = Path(source)
    else:
        target_path = RESTAURANTS_PATH

    if not target_path.exists():
        return []

    try:
        with target_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    restaurants: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        cleaned = clean_restaurant(item)
        if cleaned is not None:
            restaurants.append(cleaned)

    return restaurants


def load_user_interactions(user_id: str) -> list[dict]:
    """
    Load interaction history for a given user.

    Args:
        user_id: Unique user identifier.

    Returns:
        List of interaction records.

    Expected output schema per record:
        {
            "user_id": str,
            "business_id": str,
            "interaction_type": str,   # "viewed" | "clicked" | "saved" | "liked"
            "interaction_value": float,
            "timestamp": str,          # ISO 8601
            "day_of_week": str,
            "time_bucket": str,        # "morning" | "afternoon" | "evening" | "night"
            "inferred_food_tags": list[str],
        }
    """
    if not user_id:
        return []

    if not USER_INTERACTIONS_PATH.exists():
        return []

    try:
        with USER_INTERACTIONS_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    return [
        record
        for record in payload
        if isinstance(record, dict) and str(record.get("user_id", "")) == str(user_id)
    ]


def load_synthetic_user_profiles() -> list[dict]:
    """Load small questionnaire-based synthetic user profiles for local testing."""
    if not SYNTHETIC_USER_PROFILES_PATH.exists():
        return []

    try:
        with SYNTHETIC_USER_PROFILES_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    return [item for item in payload if isinstance(item, dict)]


def clean_restaurant(raw: dict) -> Optional[dict]:
    """
    Normalize a single raw restaurant record from the API.
    Returns None if the record is missing critical fields.
    """
    if not isinstance(raw, dict):
        return None

    business_id = str(raw.get("business_id", "")).strip()
    name = str(raw.get("name", "")).strip()

    if not business_id or not name:
        return None

    cleaned = dict(raw)
    coordinates = raw.get("coordinates", {})

    latitude = _optional_float(raw.get("latitude"))
    longitude = _optional_float(raw.get("longitude"))

    if isinstance(coordinates, dict):
        if latitude is None:
            latitude = _optional_float(coordinates.get("latitude"))
        if longitude is None:
            longitude = _optional_float(coordinates.get("longitude"))

    cleaned["latitude"] = latitude
    cleaned["longitude"] = longitude

    return cleaned
