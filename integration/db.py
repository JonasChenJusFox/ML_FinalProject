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

import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DBNAME = os.getenv("MONGO_DBNAME", "NearBite")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in .env")

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[MONGO_DBNAME]


def get_collection(name: str):
    return db[name]