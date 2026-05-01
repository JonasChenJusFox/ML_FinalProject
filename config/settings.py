"""Environment-driven settings: Yelp, database URL, embedding model, and app defaults.

Values come from ``os.environ`` after ``load_dotenv()``; use ``.env`` locally (see ``.env.example``).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Yelp Fusion API ---
YELP_API_KEY = os.getenv("YELP_API_KEY", "")
YELP_BASE_URL = "https://api.yelp.com/v3"
YELP_DAILY_LIMIT = 500  # requests/day; cache responses locally

# --- Database (PostgreSQL + pgvector) ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nearbite")

# --- Embedding model ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- App defaults ---
DEFAULT_CITY = "New York City"
DEFAULT_TOP_K = 20
MAX_DISTANCE_KM = 10.0
