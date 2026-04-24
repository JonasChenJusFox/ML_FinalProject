"""
integration/db.py
Owner: Jonas Chen

Responsibilities:
- Loads MongoDB configuration from environment variables
- Creates the shared MongoDB client connection
- Exposes the NearBite database handle
- Provides helper functions for collection access
- Exposes frontend-facing persistence helpers for reviews, likes, saves, and interactions
- Re-exports user account and profile operations from user_repo through a stable access layer
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DBNAME = os.getenv("MONGO_DBNAME", "NearBite")
REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DB_PATH = REPO_ROOT / "data" / "local_db.json"


def _serialize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _load_local_db() -> dict:
    if not LOCAL_DB_PATH.exists():
        return {}
    try:
        with LOCAL_DB_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


def _write_local_db(payload: dict) -> None:
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_DB_PATH.open("w", encoding="utf-8") as file:
        json.dump(_serialize(payload), file, ensure_ascii=False, indent=2)


def _matches_filter(document: dict, query: dict) -> bool:
    for key, expected in query.items():
        if document.get(key) != expected:
            return False
    return True


class _LocalCursor(list):
    def sort(self, key: str, direction: int):
        reverse = int(direction) < 0
        super().sort(key=lambda item: item.get(key), reverse=reverse)
        return self


class _LocalCollection:
    def __init__(self, name: str):
        self.name = name

    def _get_store(self) -> dict:
        payload = _load_local_db()
        if self.name not in payload or not isinstance(payload.get(self.name), list):
            payload[self.name] = []
        return payload

    def find_one(self, query: dict) -> dict | None:
        payload = self._get_store()
        for item in payload.get(self.name, []):
            if isinstance(item, dict) and _matches_filter(item, query):
                return dict(item)
        return None

    def insert_one(self, document: dict) -> None:
        payload = self._get_store()
        payload[self.name].append(dict(document))
        _write_local_db(payload)

    def update_one(self, query: dict, update: dict, upsert: bool = False) -> None:
        payload = self._get_store()
        docs = payload.get(self.name, [])
        set_values = update.get("$set", {}) if isinstance(update, dict) else {}
        unset_values = update.get("$unset", {}) if isinstance(update, dict) else {}

        for index, item in enumerate(docs):
            if not isinstance(item, dict):
                continue
            if _matches_filter(item, query):
                merged = dict(item)
                if isinstance(set_values, dict):
                    merged.update(set_values)
                if isinstance(unset_values, dict):
                    for key in unset_values:
                        merged.pop(key, None)
                docs[index] = merged
                _write_local_db(payload)
                return

        if upsert:
            new_doc = dict(query)
            if isinstance(set_values, dict):
                new_doc.update(set_values)
            docs.append(new_doc)
            _write_local_db(payload)

    def delete_one(self, query: dict) -> None:
        payload = self._get_store()
        docs = payload.get(self.name, [])
        for index, item in enumerate(docs):
            if isinstance(item, dict) and _matches_filter(item, query):
                del docs[index]
                _write_local_db(payload)
                return

    def find(self, query: dict, projection: dict | None = None):
        payload = self._get_store()
        output = []

        for item in payload.get(self.name, []):
            if not isinstance(item, dict):
                continue
            if not _matches_filter(item, query):
                continue

            if not projection:
                output.append(dict(item))
                continue

            projected = {}
            for key, include in projection.items():
                if not include or key == "_id":
                    continue
                if key in item:
                    projected[key] = item[key]
            output.append(projected)

        return _LocalCursor(output)


def _init_mongo():
    if not MONGO_URI:
        return None, None
    try:
        mongo_client = MongoClient(
            MONGO_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=1500,
        )
        mongo_client.admin.command("ping")
        return mongo_client, mongo_client[MONGO_DBNAME]
    except Exception:
        return None, None

client, db = _init_mongo()
USE_LOCAL_DB = db is None


def get_collection(name: str):
    if USE_LOCAL_DB:
        return _LocalCollection(name)
    return db[name]


# ---------------------------------------------------------------------------
# User account and profile compatibility layer
# Import after get_collection is defined to avoid circular import issues.
# ---------------------------------------------------------------------------

from integration.user_repo import (
    clear_user_profile as _clear_user_profile,
    create_user as _create_user,
    delete_user_by_username as _delete_user_by_username,
    find_user_by_credentials as _find_user_by_credentials,
    find_user_by_username as _find_user_by_username,
    get_secret_question_prompt as _get_secret_question_prompt,
    get_secret_questions as _get_secret_questions,
    get_user_profile as _get_user_profile,
    has_secret_question as _has_secret_question,
    is_valid_secret_question as _is_valid_secret_question,
    reset_user_password as _reset_user_password,
    save_user_profile as _save_user_profile,
    set_personalization_state as _set_personalization_state,
    set_secret_question as _set_secret_question,
    verify_secret_question_answer as _verify_secret_question_answer,
)


def get_secret_questions() -> list[str]:
    return _get_secret_questions()


def is_valid_secret_question(secret_question_prompt: str) -> bool:
    return _is_valid_secret_question(secret_question_prompt)


def create_user(
    username: str,
    password: str,
    display_name: str,
    secret_question_prompt: str,
    secret_answer: str,
) -> None:
    _create_user(
        username=username,
        password=password,
        display_name=display_name,
        secret_question_prompt=secret_question_prompt,
        secret_answer=secret_answer,
    )


def find_user_by_username(username: str) -> dict | None:
    return _find_user_by_username(username)


def find_user_by_credentials(
    identifier: str,
    password: str,
    *,
    identity_type: str = "username",
) -> dict | None:
    return _find_user_by_credentials(
        identifier,
        password,
        identity_type=identity_type,
    )


def reset_user_password(username: str, new_password: str) -> None:
    _reset_user_password(username, new_password)


def get_secret_question_prompt(username: str) -> str:
    return _get_secret_question_prompt(username)


def has_secret_question(username: str) -> bool:
    return _has_secret_question(username)


def verify_secret_question_answer(username: str, secret_answer: str) -> bool:
    return _verify_secret_question_answer(username, secret_answer)


def set_secret_question(username: str, secret_question_prompt: str, secret_answer: str) -> None:
    _set_secret_question(username, secret_question_prompt, secret_answer)


def get_user_profile(username: str) -> dict | None:
    return _get_user_profile(username)


def save_user_profile(username: str, questionnaire_answers: dict) -> None:
    _save_user_profile(username, questionnaire_answers)


def set_personalization_state(
    username: str,
    enabled: bool,
    *,
    frozen_personalization: dict | None = None,
) -> None:
    _set_personalization_state(
        username,
        enabled,
        frozen_personalization=frozen_personalization,
    )


def clear_user_profile(username: str) -> None:
    _clear_user_profile(username)


def delete_user_by_username(username: str) -> None:
    _delete_user_by_username(username)


# ---------------------------------------------------------------------------
# Saved, liked, review, and interaction storage
# ---------------------------------------------------------------------------

saved_collection = get_collection("saved_restaurants")
liked_collection = get_collection("liked_restaurants")
reviews_collection = get_collection("restaurant_reviews")
interaction_collection = get_collection("user_interactions")

REVIEW_SENTIMENT_TO_WEIGHT = {
    "love": 2.0,
    "neutral": 0.0,
    "hate": -2.0,
}


def get_saved_restaurant_ids(username: str) -> list[str]:
    docs = saved_collection.find(
        {"username": username},
        {"business_id": 1, "_id": 0},
    )
    return [doc["business_id"] for doc in docs if "business_id" in doc]


def get_liked_restaurant_ids(username: str) -> list[str]:
    docs = liked_collection.find(
        {"username": username},
        {"business_id": 1, "_id": 0},
    )
    return [doc["business_id"] for doc in docs if "business_id" in doc]


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


def delete_all_saved_restaurants_for_user(username: str) -> None:
    for business_id in get_saved_restaurant_ids(username):
        saved_collection.delete_one(
            {
                "username": username,
                "business_id": business_id,
            }
        )


def like_restaurant_for_user(username: str, business_id: str) -> None:
    liked_collection.update_one(
        {
            "username": username,
            "business_id": business_id,
        },
        {
            "$set": {
                "username": username,
                "business_id": business_id,
                "liked_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def unlike_restaurant_for_user(username: str, business_id: str) -> None:
    liked_collection.delete_one(
        {
            "username": username,
            "business_id": business_id,
        }
    )


def delete_all_liked_restaurants_for_user(username: str) -> None:
    for business_id in get_liked_restaurant_ids(username):
        liked_collection.delete_one(
            {
                "username": username,
                "business_id": business_id,
            }
        )


def normalize_review_sentiment(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in REVIEW_SENTIMENT_TO_WEIGHT:
        return normalized

    try:
        rating = float(value)
    except (TypeError, ValueError):
        return "neutral"

    if rating >= 4.0:
        return "love"
    if rating <= 2.0:
        return "hate"
    return "neutral"


def review_sentiment_to_weight(sentiment: object) -> float:
    normalized = normalize_review_sentiment(sentiment)
    return REVIEW_SENTIMENT_TO_WEIGHT.get(normalized, 0.0)


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
    sentiment: str,
    comment: str,
) -> None:
    existing = get_user_review(username, business_id)
    created_at = existing.get("created_at") if existing else datetime.utcnow()
    updated_at = datetime.utcnow()
    exclude_from_personalization = bool(existing.get("exclude_from_personalization", False)) if existing else False
    normalized_sentiment = normalize_review_sentiment(sentiment)

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
                "sentiment": normalized_sentiment,
                "comment": str(comment or "").strip(),
                "exclude_from_personalization": exclude_from_personalization,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        },
        upsert=True,
    )
    reviews_collection.update_one(
        {
            "username": username,
            "business_id": business_id,
        },
        {
            "$unset": {
                "rating": "",
            }
        },
    )


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


# ---------------------------------------------------------------------------
# Personalization summary helpers
# ---------------------------------------------------------------------------

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
    user = find_user_by_username(username) or {}
    if user.get("personalization_enabled", True) is False:
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
    cursor = interaction_collection.find({"username": username}).sort("created_at", -1)
    return list(cursor)


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

    saved_ids = get_saved_restaurant_ids(username)
    liked_ids = get_liked_restaurant_ids(username)
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

    for business_id in liked_ids:
        restaurant = restaurant_index.get(business_id)
        if not restaurant:
            continue

        for category in restaurant.get("categories", [])[:3]:
            cuisine_scores[category] = cuisine_scores.get(category, 0.0) + 0.75

        borough = restaurant.get("borough")
        if borough:
            borough_scores[borough] = borough_scores.get(borough, 0.0) + 0.75

        for vibe in restaurant.get("vibes", []):
            vibe_scores[vibe] = vibe_scores.get(vibe, 0.0) + 0.75

    for review in reviews:
        business_id = review.get("business_id")
        restaurant = restaurant_index.get(business_id, review)

        review_weight = review_sentiment_to_weight(
            review.get("sentiment", review.get("rating"))
        )
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


def clear_personalization_data(username: str) -> None:
    user = find_user_by_username(username) or {}
    personalization_enabled = bool(user.get("personalization_enabled", True))

    clear_user_profile(username)
    delete_all_interactions_for_user(username)
    delete_all_saved_restaurants_for_user(username)
    delete_all_liked_restaurants_for_user(username)
    exclude_user_reviews_from_personalization(username)

    frozen_stats = None if personalization_enabled else empty_wrapped_stats()
    set_personalization_state(
        username,
        personalization_enabled,
        frozen_personalization=frozen_stats,
    )


def delete_account(username: str) -> None:
    clear_user_profile(username)
    delete_all_interactions_for_user(username)
    delete_all_saved_restaurants_for_user(username)
    delete_all_liked_restaurants_for_user(username)
    delete_all_reviews_for_user(username)
    delete_user_by_username(username)
