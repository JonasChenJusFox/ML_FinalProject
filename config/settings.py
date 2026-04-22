"""
config/settings.py
Owner: Nick

Central configuration. All API keys and environment variables are loaded here.
Never commit real keys — use a .env file (see .env.example).
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# --- Yelp Fusion API ---
YELP_API_KEY = os.getenv("YELP_API_KEY", "")
YELP_BASE_URL = "https://api.yelp.com/v3"
YELP_DAILY_LIMIT = 500  # requests/day; cache responses locally

# --- Database (PostgreSQL + pgvector) ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nearbite")

# --- Embedding model ---
# Keep this aligned with the offline-built restaurant embeddings artifacts.
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/multi-qa-mpnet-base-cos-v1",
)

# --- App defaults ---
DEFAULT_CITY = "New York City"
DEFAULT_TOP_K = 20
MAX_DISTANCE_KM = 10.0

# --- Auth email (SMTP) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "NearBite")
SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)
SMTP_USE_SSL = _env_bool("SMTP_USE_SSL", False)

# --- Auth verification ---
AUTH_VERIFICATION_CODE_TTL_MINUTES = int(
    os.getenv("AUTH_VERIFICATION_CODE_TTL_MINUTES", "10")
)
AUTH_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("AUTH_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60")
)
AUTH_VERIFICATION_MAX_ATTEMPTS = int(
    os.getenv("AUTH_VERIFICATION_MAX_ATTEMPTS", "5")
)
