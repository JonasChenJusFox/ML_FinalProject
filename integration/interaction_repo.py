"""
integration/interaction_repo.py
Owner: Jonas Chen

Responsibilities:
- Handles MongoDB reads and writes for user restaurant interactions
- Standardizes save / like / review into one normalized interaction format
- Keeps saved restaurant compatibility for existing UI/session state
- Exposes simple helpers for profile and personalization flows
"""

from __future__ import annotations

from datetime import datetime

from integration.db import get_collection

interaction_collection = get_collection("user_interactions")
saved_collection = get_collection("saved_restaurants")

VALID_INTERACTION_TYPES = {"save", "like", "review"}
VALID_REVIEW_SIGNALS = {"love", "neutral", "hate"}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _normalize_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value

    text = str(value or "").strip()
    if not text:
        return datetime.min

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min


def _normalize_interaction_type(value: object) -> str | None:
    text = str(value or "").strip().lower()
    aliases = {
        "saved": "save",
        "save": "save",
        "liked": "like",
        "like": "like",
        "review": "review",
    }
    interaction_type = aliases.get(text)
    if interaction_type in VALID_INTERACTION_TYPES:
        return interaction_type
    return None


def _normalize_review_signal(value: object) -> str | None:
    signal = str(value or "").strip().lower()
    if signal in VALID_REVIEW_SIGNALS:
        return signal
    return None


def _clean_note(note: object) -> str:
    return str(note or "").strip()


def _delete_many(collection, query: dict) -> None:
    if hasattr(collection, "delete_many"):
        collection.delete_many(query)
        return
    collection.delete_one(query)


def _normalize_interaction_doc(document: dict) -> dict | None:
    if not isinstance(document, dict):
        return None

    username = str(document.get("username") or document.get("user_id") or "").strip().lower()
    business_id = str(document.get("business_id") or "").strip()
    interaction_type = _normalize_interaction_type(
        document.get("interaction_type") or document.get("action")
    )

    if not username or not business_id or interaction_type is None:
        return None

    review_signal = _normalize_review_signal(document.get("review_signal"))
    if interaction_type == "review" and review_signal is None:
        return None

    note = _clean_note(document.get("note"))
    timestamp = (
        document.get("timestamp")
        or document.get("created_at")
        or document.get("saved_at")
        or _utcnow()
    )

    return {
        "username": username,
        "user_id": username,
        "business_id": business_id,
        "interaction_type": interaction_type,
        "review_signal": review_signal,
        "note": note,
        "timestamp": timestamp,
    }


def upsert_user_interaction(
    username: str,
    business_id: str,
    interaction_type: str,
    review_signal: str | None = None,
    note: str | None = None,
) -> None:
    normalized_username = str(username or "").strip().lower()
    normalized_business_id = str(business_id or "").strip()
    normalized_type = _normalize_interaction_type(interaction_type)

    if not normalized_username or not normalized_business_id or normalized_type is None:
        return

    normalized_review_signal = _normalize_review_signal(review_signal)
    if normalized_type == "review" and normalized_review_signal is None:
        raise ValueError("review_signal must be one of: love, neutral, hate")

    payload = {
        "username": normalized_username,
        "user_id": normalized_username,
        "business_id": normalized_business_id,
        "interaction_type": normalized_type,
        "review_signal": normalized_review_signal if normalized_type == "review" else None,
        "note": _clean_note(note),
        "timestamp": _utcnow(),
    }

    interaction_collection.update_one(
        {
            "username": normalized_username,
            "business_id": normalized_business_id,
            "interaction_type": normalized_type,
        },
        {"$set": payload},
        upsert=True,
    )


def save_restaurant_for_user(username: str, business_id: str) -> None:
    normalized_username = str(username or "").strip().lower()
    normalized_business_id = str(business_id or "").strip()
    if not normalized_username or not normalized_business_id:
        return

    saved_collection.update_one(
        {
            "username": normalized_username,
            "business_id": normalized_business_id,
        },
        {
            "$set": {
                "username": normalized_username,
                "business_id": normalized_business_id,
                "saved_at": _utcnow(),
            }
        },
        upsert=True,
    )
    upsert_user_interaction(normalized_username, normalized_business_id, "save")


def unsave_restaurant_for_user(username: str, business_id: str) -> None:
    normalized_username = str(username or "").strip().lower()
    normalized_business_id = str(business_id or "").strip()
    if not normalized_username or not normalized_business_id:
        return

    saved_collection.delete_one(
        {
            "username": normalized_username,
            "business_id": normalized_business_id,
        }
    )
    _delete_many(
        interaction_collection,
        {
            "username": normalized_username,
            "business_id": normalized_business_id,
            "interaction_type": "save",
        },
    )


def like_restaurant_for_user(username: str, business_id: str) -> None:
    upsert_user_interaction(username, business_id, "like")


def unlike_restaurant_for_user(username: str, business_id: str) -> None:
    normalized_username = str(username or "").strip().lower()
    normalized_business_id = str(business_id or "").strip()
    if not normalized_username or not normalized_business_id:
        return

    _delete_many(
        interaction_collection,
        {
            "username": normalized_username,
            "business_id": normalized_business_id,
            "interaction_type": "like",
        },
    )


def review_restaurant_for_user(
    username: str,
    business_id: str,
    review_signal: str,
    note: str | None = None,
) -> None:
    upsert_user_interaction(
        username=username,
        business_id=business_id,
        interaction_type="review",
        review_signal=review_signal,
        note=note,
    )


def get_user_interactions(username: str) -> list[dict]:
    normalized_username = str(username or "").strip().lower()
    if not normalized_username:
        return []

    normalized_by_key: dict[tuple[str, str], dict] = {}

    raw_documents = list(interaction_collection.find({"username": normalized_username}))
    raw_documents.extend(interaction_collection.find({"user_id": normalized_username}))

    for document in raw_documents:
        normalized = _normalize_interaction_doc(document)
        if normalized is None:
            continue
        key = (normalized["business_id"], normalized["interaction_type"])
        existing = normalized_by_key.get(key)
        if existing is None or _normalize_timestamp(normalized["timestamp"]) > _normalize_timestamp(existing["timestamp"]):
            normalized_by_key[key] = normalized

    existing_save_keys = {
        key
        for key in normalized_by_key
        if key[1] == "save"
    }
    for document in saved_collection.find({"username": normalized_username}):
        business_id = str(document.get("business_id") or "").strip()
        key = (business_id, "save")
        if not business_id or key in existing_save_keys:
            continue
        normalized_by_key[key] = {
            "username": normalized_username,
            "user_id": normalized_username,
            "business_id": business_id,
            "interaction_type": "save",
            "review_signal": None,
            "note": "",
            "timestamp": document.get("saved_at") or _utcnow(),
        }

    interactions = list(normalized_by_key.values())
    interactions.sort(key=lambda item: _normalize_timestamp(item.get("timestamp")), reverse=True)
    return interactions


def get_saved_restaurant_ids(username: str) -> list[str]:
    return [
        record["business_id"]
        for record in get_user_interactions(username)
        if record.get("interaction_type") == "save"
    ]


def get_liked_restaurant_ids(username: str) -> list[str]:
    return [
        record["business_id"]
        for record in get_user_interactions(username)
        if record.get("interaction_type") == "like"
    ]


def get_user_interaction_map(username: str) -> dict[str, dict]:
    interaction_map: dict[str, dict] = {}

    for record in get_user_interactions(username):
        business_id = record.get("business_id")
        if not business_id:
            continue

        entry = interaction_map.setdefault(
            business_id,
            {
                "business_id": business_id,
                "saved": False,
                "liked": False,
                "review_signal": None,
                "note": "",
                "last_timestamp": None,
            },
        )

        interaction_type = record.get("interaction_type")
        if interaction_type == "save":
            entry["saved"] = True
        elif interaction_type == "like":
            entry["liked"] = True
        elif interaction_type == "review":
            entry["review_signal"] = record.get("review_signal")
            entry["note"] = _clean_note(record.get("note"))

        timestamp = record.get("timestamp")
        if entry["last_timestamp"] is None or _normalize_timestamp(timestamp) > _normalize_timestamp(entry["last_timestamp"]):
            entry["last_timestamp"] = timestamp

    return interaction_map


def get_user_interaction_records(username: str) -> list[dict]:
    records = list(get_user_interaction_map(username).values())
    records.sort(key=lambda item: _normalize_timestamp(item.get("last_timestamp")), reverse=True)
    return records
