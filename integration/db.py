"""
integration/db.py
Owner: Jonas Chen

Responsibilities:
- Loads MongoDB configuration from environment variables
- Creates the shared MongoDB client connection
- Exposes the NearBite database handle
- Provides helper functions for collection access
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

        for index, item in enumerate(docs):
            if not isinstance(item, dict):
                continue
            if _matches_filter(item, query):
                merged = dict(item)
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