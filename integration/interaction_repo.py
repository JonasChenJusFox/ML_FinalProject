"""
integration/interaction_repo.py
Owner: Jonas Chen

Responsibilities:
- Handles MongoDB reads and writes for user restaurant interactions
- Stores and removes saved restaurants for each user
- Retrieves saved restaurant ids for profile and recommendation flows
- Keeps interaction persistence separate from UI logic
"""

from __future__ import annotations

from datetime import datetime

from integration.db import get_collection

saved_collection = get_collection("saved_restaurants")


def save_restaurant_for_user(username: str, business_id: str) -> None:
    saved_collection.update_one(
        {
            "username": username,
            "business_id": business_id,
        },
        {
            "$set": {
                "username": username,
                "business_id": business_id,
                "saved_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def unsave_restaurant_for_user(username: str, business_id: str) -> None:
    saved_collection.delete_one(
        {
            "username": username,
            "business_id": business_id,
        }
    )


def get_saved_restaurant_ids(username: str) -> list[str]:
    docs = saved_collection.find(
        {"username": username},
        {"business_id": 1, "_id": 0},
    )
    return [doc["business_id"] for doc in docs if "business_id" in doc]


def delete_all_saved_restaurants_for_user(username: str) -> None:
    for business_id in get_saved_restaurant_ids(username):
        saved_collection.delete_one(
            {
                "username": username,
                "business_id": business_id,
            }
        )
