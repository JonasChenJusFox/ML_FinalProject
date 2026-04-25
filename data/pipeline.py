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
            "username": str,
            "business_id": str,
            "interaction_type": str,   # "save" | "like" | "review"
            "review_signal": str | None,
            "note": str,
            "timestamp": str,
        }
    """
    if not user_id:
        return []

    try:
        from integration.interaction_repo import get_user_interactions

        mongo_records = get_user_interactions(str(user_id))
        if mongo_records:
            return mongo_records
    except Exception:
        pass

    if not USER_INTERACTIONS_PATH.exists():
        return []

    try:
        with USER_INTERACTIONS_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    normalized_records: list[dict] = []
    normalized_user_id = str(user_id).strip().lower()

    for record in payload:
        if not isinstance(record, dict):
            continue

        record_user_id = str(record.get("user_id", "")).strip().lower()
        if record_user_id != normalized_user_id:
            continue

        interaction_type = str(record.get("interaction_type", "")).strip().lower()
        interaction_aliases = {
            "saved": "save",
            "save": "save",
            "liked": "like",
            "like": "like",
            "review": "review",
        }
        normalized_type = interaction_aliases.get(interaction_type)
        if normalized_type is None:
            continue

        review_signal = str(record.get("review_signal", "")).strip().lower() or None
        if normalized_type == "review" and review_signal not in {"love", "neutral", "hate"}:
            continue

        normalized_records.append(
            {
                "user_id": normalized_user_id,
                "username": normalized_user_id,
                "business_id": str(record.get("business_id", "")).strip(),
                "interaction_type": normalized_type,
                "review_signal": review_signal,
                "note": str(record.get("note", "")).strip(),
                "timestamp": record.get("timestamp", ""),
            }
        )

    return [record for record in normalized_records if record.get("business_id")]


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

    return raw
