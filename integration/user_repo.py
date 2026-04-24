"""
integration/user_repo.py
Owner: Jonas Chen

Responsibilities:
- Handles MongoDB reads and writes for user accounts
- Stores and retrieves onboarding questionnaire answers
- Supports username/password authentication and password reset flows
- Normalizes questionnaire answers and builds embedding-ready profile text
- Hashes and verifies passwords and secret answers
- Keeps database access separate from Streamlit UI logic
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import secrets
from typing import Any

from config.settings import EMBEDDING_MODEL
from integration.db import get_collection

users_collection = get_collection("users")
profiles_collection = get_collection("user_profiles")

SECRET_QUESTIONS = [
    "What was the name of your first pet?",
    "What street did you grow up on?",
    "What was your childhood nickname?",
    "What was the first concert you attended?",
    "What city were you born in?",
    "What was the name of your favorite teacher?",
    "What was the make of your first car?",
]


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16


def hash_secret(
    secret: str,
    *,
    salt_hex: str | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        iterations,
    )
    return digest.hex(), salt.hex()


def verify_secret(
    secret: str,
    expected_hash: str,
    salt_hex: str,
    *,
    iterations: int = PBKDF2_ITERATIONS,
) -> bool:
    actual_hash, _ = hash_secret(secret, salt_hex=salt_hex, iterations=iterations)
    return hmac.compare_digest(actual_hash, expected_hash)


# ---------------------------------------------------------------------------
# Questionnaire normalization and profile text
# ---------------------------------------------------------------------------

_PRICE_ALIAS_TO_LABEL = {
    "$": "cheap",
    "$$": "moderate",
    "$$$": "expensive",
    "$$$$": "luxury",
    "1": "cheap",
    "2": "moderate",
    "3": "expensive",
    "4": "luxury",
    "cheap": "cheap",
    "budget": "cheap",
    "affordable": "cheap",
    "inexpensive": "cheap",
    "moderate": "moderate",
    "mid range": "moderate",
    "mid-range": "moderate",
    "reasonably priced": "moderate",
    "expensive": "expensive",
    "pricey": "expensive",
    "upscale": "expensive",
    "luxury": "luxury",
    "fine dining": "luxury",
    "premium": "luxury",
    "high end": "luxury",
    "high-end": "luxury",
}

_PRICE_LEVELS = {
    "cheap": 1.0,
    "moderate": 2.0,
    "expensive": 3.0,
    "luxury": 4.0,
}

TRAVEL_TO_MAX_KM = {
    "Walking distance (< 10 min / ~0.5 mi)": 0.8,
    "Short commute (10–20 min / ~1 mi)": 1.6,
    "Across the neighborhood (20–35 min)": 5.0,
    "Anywhere in the city": 20.0,
}

NOVELTY_TO_LEVEL = {
    "stick to what i know": 0.1,
    "mix of both": 0.5,
    "try new things": 0.9,
}


def canonicalize_price_label(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        rounded = int(round(float(value)))
        return _PRICE_ALIAS_TO_LABEL.get(str(rounded), "")

    text = str(value).strip().lower()
    if not text:
        return ""

    return _PRICE_ALIAS_TO_LABEL.get(text, "")


def price_level_value(value: Any) -> float:
    canonical = canonicalize_price_label(value)
    if canonical:
        return _PRICE_LEVELS.get(canonical, 0.0)

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def normalize_answers(raw_answers: dict) -> dict:
    answers = raw_answers if isinstance(raw_answers, dict) else {}

    top_cuisines = _clean_list(answers.get("top_cuisines", []))
    cravings = _clean_list(answers.get("craving_preferences", []))
    vibes = _clean_list(answers.get("vibes_dining_style", []))
    dietary = _clean_list(answers.get("dietary_restrictions", []))
    meals = _clean_list(answers.get("typical_meals", []))
    decision = _clean_list(answers.get("decision_criteria", []))
    dishes = _clean_list(answers.get("favorite_dishes", []))

    loved = _clean_list(answers.get("loved_restaurants", []))
    wishlist = _clean_list(answers.get("wishlist_restaurants", []))
    frequent = _clean_list(answers.get("frequent_restaurants", []))
    aspirational = _clean_list(answers.get("aspirational_restaurants", []))

    novelty = str(answers.get("novelty_preference", "")).strip().lower()
    price_label = canonicalize_price_label(answers.get("price_comfort_level", "moderate")) or "moderate"
    adventurousness = answers.get("adventurousness", 3)

    try:
        adventurousness_value = int(adventurousness)
    except (TypeError, ValueError):
        adventurousness_value = 3
    adventurousness_value = max(1, min(5, adventurousness_value))

    travel = str(answers.get("travel_willingness", "")).strip()
    if travel not in TRAVEL_TO_MAX_KM:
        travel = "Short commute (10–20 min / ~1 mi)"

    return {
        "cuisine_pref": [item.lower() for item in top_cuisines],
        "craving_tags": [item.lower() for item in cravings],
        "price_level": {
            "label": price_label,
            "numeric": int(round(price_level_value(price_label) or 2.0)),
        },
        "vibe_tags": [item.lower() for item in vibes],
        "dietary_tags": [item.lower() for item in dietary if item.lower() != "none"],
        "adventure_level": round((adventurousness_value - 1) / 4, 3),
        "max_travel_km": TRAVEL_TO_MAX_KM.get(travel, 1.6),
        "company_tags": [str(answers.get("dining_company", "")).strip().lower()] if str(answers.get("dining_company", "")).strip() else [],
        "meal_tags": [item.lower() for item in meals],
        "decision_weights": {item.lower(): 1.0 for item in decision},
        "novelty_level": NOVELTY_TO_LEVEL.get(novelty, 0.5),
        "dish_tags": [item.lower() for item in dishes],
        "restaurant_affinity_terms": [
            item.lower()
            for item in (loved + frequent + wishlist + aspirational)
        ],
    }


def build_profile_text(raw_answers: dict) -> str:
    answers = raw_answers if isinstance(raw_answers, dict) else {}
    normalized = normalize_answers(answers)

    parts: list[str] = []

    for key in [
        "top_cuisines",
        "craving_preferences",
        "vibes_dining_style",
        "dietary_restrictions",
        "typical_meals",
        "decision_criteria",
        "favorite_dishes",
        "loved_restaurants",
        "wishlist_restaurants",
        "frequent_restaurants",
        "aspirational_restaurants",
    ]:
        value = answers.get(key, [])
        if isinstance(value, list) and value:
            parts.append(f"{key}: " + ", ".join(str(item).strip() for item in value if str(item).strip()))

    price = canonicalize_price_label(answers.get("price_comfort_level", "moderate")) or "moderate"
    travel = str(answers.get("travel_willingness", "")).strip()
    company = str(answers.get("dining_company", "")).strip()
    novelty = str(answers.get("novelty_preference", "")).strip()
    adventurousness = answers.get("adventurousness", 3)

    parts.append(f"price comfort: {price}")
    if travel:
        parts.append(f"travel willingness: {travel}")
    if company:
        parts.append(f"dining company: {company}")
    if novelty:
        parts.append(f"novelty preference: {novelty}")
    parts.append(f"adventurousness: {adventurousness}")

    affinity_terms = normalized.get("restaurant_affinity_terms", [])
    if affinity_terms:
        parts.append("restaurant affinity: " + ", ".join(affinity_terms))

    return " | ".join(part for part in parts if part).strip()


# ---------------------------------------------------------------------------
# User account and profile persistence
# ---------------------------------------------------------------------------


def _build_password_fields(password: str) -> dict:
    password_hash, password_salt = hash_secret(password)
    return {
        "password": None,
        "password_hash": password_hash,
        "password_salt": password_salt,
        "password_algorithm": "pbkdf2_sha256",
    }


def _normalize_secret_answer(answer: str) -> str:
    return " ".join(str(answer or "").strip().lower().split())


def _build_secret_answer_fields(secret_answer: str) -> dict:
    normalized_answer = _normalize_secret_answer(secret_answer)
    secret_answer_hash, secret_answer_salt = hash_secret(normalized_answer)
    return {
        "secret_answer_hash": secret_answer_hash,
        "secret_answer_salt": secret_answer_salt,
    }


def _verify_user_password(user: dict, password: str) -> bool:
    password_hash = user.get("password_hash")
    password_salt = user.get("password_salt")

    if password_hash and password_salt:
        return verify_secret(password, password_hash, password_salt)

    legacy_password = user.get("password")
    return isinstance(legacy_password, str) and hmac.compare_digest(legacy_password, password)


def get_secret_questions() -> list[str]:
    return list(SECRET_QUESTIONS)


def is_valid_secret_question(secret_question_prompt: str) -> bool:
    return secret_question_prompt in SECRET_QUESTIONS


def create_user(
    username: str,
    password: str,
    display_name: str,
    secret_question_prompt: str,
    secret_answer: str,
) -> None:
    users_collection.insert_one(
        {
            "username": username,
            "email": "",
            "display_name": display_name,
            "created_at": datetime.utcnow(),
            "secret_question_prompt": secret_question_prompt,
            "personalization_enabled": True,
            "frozen_personalization": None,
            **_build_password_fields(password),
            **_build_secret_answer_fields(secret_answer),
        }
    )


def find_user_by_username(username: str) -> dict | None:
    return users_collection.find_one({"username": username})


def find_user_by_email(email: str) -> dict | None:
    return users_collection.find_one({"email": email})


def find_user_by_identity(identifier: str, identity_type: str = "username") -> dict | None:
    normalized_type = (identity_type or "username").strip().lower()
    if normalized_type == "email":
        return find_user_by_email(identifier)
    return find_user_by_username(identifier)


def find_user_by_credentials(
    identifier: str,
    password: str,
    *,
    identity_type: str = "username",
) -> dict | None:
    user = find_user_by_identity(identifier, identity_type=identity_type)
    if not user or not _verify_user_password(user, password):
        return None

    if user.get("password") and not user.get("password_hash"):
        reset_user_password(user["username"], password)
        user = find_user_by_username(user["username"]) or user

    return user


def reset_user_password(username: str, new_password: str) -> None:
    users_collection.update_one(
        {"username": username},
        {
            "$set": {
                **_build_password_fields(new_password),
                "updated_at": datetime.utcnow(),
            }
        },
    )


def clear_user_profile(username: str) -> None:
    profiles_collection.delete_one({"username": username})


def get_secret_question_prompt(username: str) -> str:
    user = find_user_by_username(username) or {}
    return str(user.get("secret_question_prompt", "") or "")


def has_secret_question(username: str) -> bool:
    return bool(get_secret_question_prompt(username))


def verify_secret_question_answer(username: str, secret_answer: str) -> bool:
    user = find_user_by_username(username) or {}
    expected_hash = user.get("secret_answer_hash")
    salt = user.get("secret_answer_salt")

    if not expected_hash or not salt:
        return False

    return verify_secret(
        _normalize_secret_answer(secret_answer),
        expected_hash,
        salt,
    )


def set_secret_question(username: str, secret_question_prompt: str, secret_answer: str) -> None:
    existing = find_user_by_username(username) or {}
    if existing.get("secret_question_prompt"):
        return

    users_collection.update_one(
        {"username": username},
        {
            "$set": {
                "secret_question_prompt": secret_question_prompt,
                **_build_secret_answer_fields(secret_answer),
                "updated_at": datetime.utcnow(),
            }
        },
    )


def is_personalization_enabled(username: str) -> bool:
    user = find_user_by_username(username) or {}
    return bool(user.get("personalization_enabled", True))


def set_personalization_state(
    username: str,
    enabled: bool,
    *,
    frozen_personalization: dict | None = None,
) -> None:
    users_collection.update_one(
        {"username": username},
        {
            "$set": {
                "personalization_enabled": bool(enabled),
                "frozen_personalization": frozen_personalization,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def delete_user_by_username(username: str) -> None:
    users_collection.delete_one({"username": username})


def save_user_profile(username: str, questionnaire_answers: dict) -> None:
    normalized_features = normalize_answers(questionnaire_answers)
    profile_text = build_profile_text(questionnaire_answers)

    existing = profiles_collection.find_one({"username": username}) or {}
    existing_latest_embedding = existing.get("latest_embedding")

    profiles_collection.update_one(
        {"username": username},
        {
            "$set": {
                "username": username,
                "raw_answers": questionnaire_answers,
                "normalized_features": normalized_features,
                "profile_text": profile_text,
                "latest_embedding": existing_latest_embedding,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def get_user_profile(username: str) -> dict | None:
    return profiles_collection.find_one({"username": username})


def update_latest_embedding(username: str, embedding_vector: list[float]) -> None:
    profiles_collection.update_one(
        {"username": username},
        {
            "$set": {
                "latest_embedding": {
                    "vector": embedding_vector,
                    "model_name": EMBEDDING_MODEL,
                    "updated_at": datetime.utcnow(),
                },
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
