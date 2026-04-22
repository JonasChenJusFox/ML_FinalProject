"""
integration/review_repo.py
Owner: Jonas Chen

Responsibilities:
- Stores user-authored restaurant reviews
- Returns restaurant review feeds visible to all users
- Returns per-user review history for profile and recommendation signals
"""

from __future__ import annotations

from datetime import datetime

from integration.db import get_collection

reviews_collection = get_collection("restaurant_reviews")


def _safe_rating(value: object) -> float:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        rating = 0.0
    return round(max(0.0, min(5.0, rating)), 1)


def upsert_restaurant_review(
    *,
    username: str,
    display_name: str,
    business_id: str,
    restaurant_name: str,
    restaurant_address: str,
    restaurant_borough: str,
    restaurant_categories: list[str],
    restaurant_price: str,
    rating: float,
    comment: str,
) -> None:
    existing = get_user_review(username, business_id)
    created_at = existing.get("created_at") if existing else datetime.utcnow()
    updated_at = datetime.utcnow()
    exclude_from_personalization = bool(existing.get("exclude_from_personalization", False)) if existing else False

    reviews_collection.update_one(
        {
            "username": username,
            "business_id": business_id,
        },
        {
            "$set": {
                "username": username,
                "display_name": display_name or username,
                "business_id": business_id,
                "restaurant_name": restaurant_name,
                "restaurant_address": restaurant_address,
                "restaurant_borough": restaurant_borough,
                "restaurant_categories": list(restaurant_categories or []),
                "restaurant_price": restaurant_price,
                "rating": _safe_rating(rating),
                "comment": str(comment or "").strip(),
                "exclude_from_personalization": exclude_from_personalization,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        },
        upsert=True,
    )


def get_reviews_for_restaurant(business_id: str) -> list[dict]:
    cursor = reviews_collection.find({"business_id": business_id}).sort("updated_at", -1)
    return list(cursor)


def get_user_review(username: str, business_id: str) -> dict | None:
    return reviews_collection.find_one(
        {
            "username": username,
            "business_id": business_id,
        }
    )


def get_user_reviews(username: str, *, include_excluded: bool = True) -> list[dict]:
    cursor = reviews_collection.find({"username": username}).sort("updated_at", -1)
    reviews = list(cursor)
    if include_excluded:
        return reviews
    return [review for review in reviews if not review.get("exclude_from_personalization", False)]


def exclude_user_reviews_from_personalization(username: str) -> None:
    for review in get_user_reviews(username):
        business_id = review.get("business_id")
        if not business_id:
            continue
        reviews_collection.update_one(
            {
                "username": username,
                "business_id": business_id,
            },
            {
                "$set": {
                    "exclude_from_personalization": True,
                    "updated_at": datetime.utcnow(),
                }
            },
        )


def delete_all_reviews_for_user(username: str) -> None:
    for review in get_user_reviews(username):
        business_id = review.get("business_id")
        if not business_id:
            continue
        reviews_collection.delete_one(
            {
                "username": username,
                "business_id": business_id,
            }
        )


def get_user_reviewed_business_ids(username: str) -> list[str]:
    return [
        doc.get("business_id", "")
        for doc in get_user_reviews(username)
        if doc.get("business_id")
    ]
