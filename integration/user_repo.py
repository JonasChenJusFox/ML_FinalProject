"""
integration/user_repo.py
Owner: Jonas Chen

Responsibilities:
- Handles MongoDB reads and writes for user accounts
- Stores and retrieves onboarding questionnaire answers
- Supports username/password authentication and password reset flows
- Keeps database access separate from Streamlit UI logic
"""

from __future__ import annotations

from datetime import datetime
import hmac

from config.settings import EMBEDDING_MODEL
from integration.auth_security import hash_secret, verify_secret
from integration.db import get_collection
from integration.user_profile_model import build_profile_text, normalize_answers

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
