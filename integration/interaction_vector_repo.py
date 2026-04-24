"""Persistence helpers for interaction-based user embedding vectors.

This module provides a small save/read layer for interaction vectors so
callers can cache computed vectors in the database and avoid recomputation
on every request.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DB_PATH = REPO_ROOT / "data" / "local_db.json"


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
    def _serialize(value: Any):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): _serialize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_serialize(item) for item in value]
        return value

    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_DB_PATH.open("w", encoding="utf-8") as file:
        json.dump(_serialize(payload), file, ensure_ascii=True, indent=2)


def _local_find_one(collection: str, query: dict) -> dict | None:
    payload = _load_local_db()
    docs = payload.get(collection, [])
    if not isinstance(docs, list):
        return None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if all(doc.get(key) == value for key, value in query.items()):
            return dict(doc)
    return None


def _local_update_one(collection: str, query: dict, update: dict, upsert: bool = False) -> None:
    payload = _load_local_db()
    docs = payload.get(collection)
    if not isinstance(docs, list):
        docs = []
        payload[collection] = docs

    set_values = update.get("$set", {}) if isinstance(update, dict) else {}
    for index, doc in enumerate(docs):
        if not isinstance(doc, dict):
            continue
        if all(doc.get(key) == value for key, value in query.items()):
            merged = dict(doc)
            if isinstance(set_values, dict):
                merged.update(set_values)
            docs[index] = merged
            _write_local_db(payload)
            return

    if upsert:
        new_doc = dict(query)
        if isinstance(set_values, dict):
            new_doc.update(set_values)
        docs.append(new_doc)
        _write_local_db(payload)


def _local_delete_one(collection: str, query: dict) -> None:
    payload = _load_local_db()
    docs = payload.get(collection, [])
    if not isinstance(docs, list):
        return
    for index, doc in enumerate(docs):
        if not isinstance(doc, dict):
            continue
        if all(doc.get(key) == value for key, value in query.items()):
            del docs[index]
            _write_local_db(payload)
            return


def _find_one(collection: str, query: dict) -> dict | None:
    try:
        from integration.db import get_collection

        return get_collection(collection).find_one(query)
    except Exception:
        return _local_find_one(collection, query)


def _update_one(collection: str, query: dict, update: dict, upsert: bool = False) -> None:
    try:
        from integration.db import get_collection

        get_collection(collection).update_one(query, update, upsert=upsert)
        return
    except Exception:
        _local_update_one(collection, query, update, upsert=upsert)


def _delete_one(collection: str, query: dict) -> None:
    try:
        from integration.db import get_collection

        get_collection(collection).delete_one(query)
        return
    except Exception:
        _local_delete_one(collection, query)


def _to_float_list(values: list[Any] | None) -> list[float] | None:
    """Validate and coerce a vector payload into list[float]."""
    if not isinstance(values, list) or not values:
        return None

    output: list[float] = []
    for value in values:
        try:
            output.append(float(value))
        except (TypeError, ValueError):
            return None

    return output


def save_interaction_vector(
    username: str,
    vector: list[float],
    source: str = "interaction_weighted_avg_v1",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Upsert a user's interaction vector and metadata.

    Args:
        username: User identifier.
        vector: Normalized interaction vector to store.
        source: Source label for versioning/debugging.
        metadata: Optional extra fields (counts, business_ids, denominator, etc).
    """
    cleaned_username = str(username or "").strip()
    cleaned_vector = _to_float_list(vector)
    if not cleaned_username or cleaned_vector is None:
        return

    now = datetime.now(timezone.utc)
    payload = {
        "username": cleaned_username,
        "vector": cleaned_vector,
        "source": str(source or "interaction_weighted_avg_v1"),
        "updated_at": now,
        "dim": len(cleaned_vector),
    }
    if isinstance(metadata, dict) and metadata:
        payload["metadata"] = metadata

    _update_one(
        "interaction_vectors",
        {"username": cleaned_username},
        {"$set": payload},
        upsert=True,
    )


def get_interaction_vector(username: str) -> list[float] | None:
    """Read a user's stored interaction vector, if available and valid."""
    cleaned_username = str(username or "").strip()
    if not cleaned_username:
        return None

    document = _find_one("interaction_vectors", {"username": cleaned_username})
    if not isinstance(document, dict):
        return None

    return _to_float_list(document.get("vector"))


def get_interaction_vector_record(username: str) -> dict[str, Any] | None:
    """Return the full stored interaction-vector record for a user."""
    cleaned_username = str(username or "").strip()
    if not cleaned_username:
        return None

    document = _find_one("interaction_vectors", {"username": cleaned_username})
    if not isinstance(document, dict):
        return None

    vector = _to_float_list(document.get("vector"))
    if vector is None:
        return None

    return {
        "username": document.get("username", cleaned_username),
        "vector": vector,
        "source": document.get("source"),
        "updated_at": document.get("updated_at"),
        "dim": document.get("dim", len(vector)),
        "metadata": document.get("metadata", {}),
    }


def delete_interaction_vector(username: str) -> None:
    """Delete a user's cached interaction vector record."""
    cleaned_username = str(username or "").strip()
    if not cleaned_username:
        return

    _delete_one("interaction_vectors", {"username": cleaned_username})
