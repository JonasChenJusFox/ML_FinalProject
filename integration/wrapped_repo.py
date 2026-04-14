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

interaction_collection = get_collection("user_interactions")
saved_collection = get_collection("saved_restaurants")


def log_user_interaction(username: str, business_id: str, action: str) -> None:
    """
    Store a user interaction event in MongoDB.
    """
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


def build_wrapped_stats(username: str, restaurants: list[dict]) -> dict:
    """
    Build wrapped-style summary stats using saved restaurants and interaction history.
    """
    restaurant_index = {
        item.get("business_id"): item
        for item in restaurants
        if item.get("business_id")
    }

    saved_ids = get_saved_business_ids(username)
    interactions = get_user_interactions(username)

    cuisine_counts: dict[str, int] = {}
    borough_counts: dict[str, int] = {}
    vibe_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}

    for business_id in saved_ids:
        restaurant = restaurant_index.get(business_id)
        if not restaurant:
            continue

        for category in restaurant.get("categories", [])[:3]:
            cuisine_counts[category] = cuisine_counts.get(category, 0) + 1

        borough = restaurant.get("borough")
        if borough:
            borough_counts[borough] = borough_counts.get(borough, 0) + 1

        for vibe in restaurant.get("vibes", []):
            vibe_counts[vibe] = vibe_counts.get(vibe, 0) + 1

    for interaction in interactions:
        action = interaction.get("action")
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1

    top_cuisines = sorted(cuisine_counts, key=cuisine_counts.get, reverse=True)[:3]
    top_boroughs = sorted(borough_counts, key=borough_counts.get, reverse=True)[:3]
    top_vibes = sorted(vibe_counts, key=vibe_counts.get, reverse=True)[:3]

    return {
        "saved_count": len(saved_ids),
        "interaction_count": len(interactions),
        "top_cuisines": top_cuisines,
        "top_boroughs": top_boroughs,
        "top_vibes": top_vibes,
        "action_counts": action_counts,
    }