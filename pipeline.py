"""
data/pipeline.py
Owner: Yue

Responsibilities:
- Ingest restaurant data from Yelp Fusion API
- Clean and normalize fields
- Structure dataset for embedding and search
- Build user interaction history table (synthetic or real)
"""

from typing import Optional


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
    raise NotImplementedError("TODO (Yue): implement load_restaurants()")


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
    raise NotImplementedError("TODO (Yue): implement load_user_interactions()")


def clean_restaurant(raw: dict) -> Optional[dict]:
    """
    Normalize a single raw restaurant record from the API.
    Returns None if the record is missing critical fields.
    """
    raise NotImplementedError("TODO (Yue): implement clean_restaurant()")
