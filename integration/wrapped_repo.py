"""
integration/wrapped_repo.py
Owner: Jonas Chen

Responsibilities:
- Logs user interaction events for wrapped-style analytics
- Loads interaction history from MongoDB
- Aggregates wrapped summary signals from saved and interaction history
- Provides database-backed wrapped stats for profile and recommendation flows
"""

from __future__ import annotations

from datetime import datetime

from integration.db import get_collection
from integration.review_repo import get_user_reviews
from integration.user_repo import find_user_by_username, is_personalization_enabled

interaction_collection = get_collection("user_interactions")
saved_collection = get_collection("saved_restaurants")


def empty_wrapped_stats() -> dict:
    return {
        "saved_count": 0,
        "interaction_count": 0,
        "reviewed_count": 0,
        "top_cuisines": [],
        "top_boroughs": [],
        "top_vibes": [],
        "action_counts": {},
    }


def log_user_interaction(username: str, business_id: str, action: str) -> None:
    """
    Store a user interaction event in MongoDB.
    """
    if not is_personalization_enabled(username):
        return

    interaction_collection.insert_one(
        {
            "username": username,
            "business_id": business_id,
            "action": action,
            "created_at": datetime.utcnow(),
        }
    )


def get_user_interactions(username: str) -> list[dict]:
    """
    Return all interaction documents for a user, newest first.
    """
    cursor = interaction_collection.find({"username": username}).sort("created_at", -1)
    return list(cursor)


def get_saved_business_ids(username: str) -> list[str]:
    """
    Return saved restaurant ids for a user from MongoDB.
    """
    cursor = saved_collection.find(
        {"username": username},
        {"business_id": 1, "_id": 0},
    )
    return [doc["business_id"] for doc in cursor if "business_id" in doc]


def delete_all_interactions_for_user(username: str) -> None:
    for interaction in get_user_interactions(username):
        business_id = interaction.get("business_id")
        action = interaction.get("action")
        created_at = interaction.get("created_at")
        if not business_id or not action:
            continue
        interaction_collection.delete_one(
            {
                "username": username,
                "business_id": business_id,
                "action": action,
                "created_at": created_at,
            }
        )


def build_wrapped_stats(username: str, restaurants: list[dict]) -> dict:
    """
    Build wrapped-style summary stats using saved restaurants and interaction history.
    """
    user = find_user_by_username(username) or {}
    if user.get("personalization_enabled") is False:
        frozen = user.get("frozen_personalization")
        if isinstance(frozen, dict):
            return {
                **empty_wrapped_stats(),
                **frozen,
            }

    restaurant_index = {
        item.get("business_id"): item
        for item in restaurants
        if item.get("business_id")
    }

    saved_ids = get_saved_business_ids(username)
    interactions = get_user_interactions(username)
    reviews = get_user_reviews(username, include_excluded=False)

    cuisine_scores: dict[str, float] = {}
    borough_scores: dict[str, float] = {}
    vibe_scores: dict[str, float] = {}
    action_counts: dict[str, int] = {}

    for business_id in saved_ids:
        restaurant = restaurant_index.get(business_id)
        if not restaurant:
            continue

        for category in restaurant.get("categories", [])[:3]:
            cuisine_scores[category] = cuisine_scores.get(category, 0.0) + 1.0

        borough = restaurant.get("borough")
        if borough:
            borough_scores[borough] = borough_scores.get(borough, 0.0) + 1.0

        for vibe in restaurant.get("vibes", []):
            vibe_scores[vibe] = vibe_scores.get(vibe, 0.0) + 1.0

    for review in reviews:
        business_id = review.get("business_id")
        restaurant = restaurant_index.get(business_id, review)

        try:
            review_rating = float(review.get("rating", 0.0) or 0.0)
        except (TypeError, ValueError):
            review_rating = 0.0

        review_weight = review_rating - 3.0
        if abs(review_weight) < 0.01:
            continue

        categories = restaurant.get("categories") or review.get("restaurant_categories", [])
        if isinstance(categories, list):
            for category in categories[:3]:
                if category:
                    cuisine_scores[category] = cuisine_scores.get(category, 0.0) + review_weight

        borough = restaurant.get("borough") or review.get("restaurant_borough")
        if borough:
            borough_scores[str(borough)] = borough_scores.get(str(borough), 0.0) + review_weight

        for vibe in restaurant.get("vibes", []):
            if vibe:
                vibe_scores[vibe] = vibe_scores.get(vibe, 0.0) + review_weight

    for interaction in interactions:
        action = interaction.get("action")
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1

    top_cuisines = [
        key
        for key, score in sorted(cuisine_scores.items(), key=lambda item: item[1], reverse=True)
        if score > 0
    ][:3]
    top_boroughs = [
        key
        for key, score in sorted(borough_scores.items(), key=lambda item: item[1], reverse=True)
        if score > 0
    ][:3]
    top_vibes = [
        key
        for key, score in sorted(vibe_scores.items(), key=lambda item: item[1], reverse=True)
        if score > 0
    ][:3]

    return {
        "saved_count": len(saved_ids),
        "interaction_count": len(interactions),
        "reviewed_count": len(reviews),
        "top_cuisines": top_cuisines,
        "top_boroughs": top_boroughs,
        "top_vibes": top_vibes,
        "action_counts": action_counts,
    }
