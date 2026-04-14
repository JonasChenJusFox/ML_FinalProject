"""
integration/user_repo.py
Owner: Jonas Chen

Responsibilities:
- Handles MongoDB reads and writes for user accounts
- Stores and retrieves onboarding questionnaire answers
- Supports sign up, login, and password reset flows
- Keeps database access separate from Streamlit UI logic
"""

from __future__ import annotations

from datetime import datetime

from integration.db import get_collection

users_collection = get_collection("users")
profiles_collection = get_collection("user_profiles")


def create_user(username: str, email: str, password: str, display_name: str) -> None:
    users_collection.insert_one(
        {
            "username": username,
            "email": email,
            "password": password,
            "display_name": display_name,
            "created_at": datetime.utcnow(),
        }
    )


def find_user_by_username(username: str) -> dict | None:
    return users_collection.find_one({"username": username})


def find_user_by_credentials(username: str, password: str) -> dict | None:
    return users_collection.find_one(
        {
            "username": username,
            "password": password,
        }
    )


def reset_user_password(username: str, new_password: str) -> None:
    users_collection.update_one(
        {"username": username},
        {"$set": {"password": new_password, "updated_at": datetime.utcnow()}},
    )


def save_user_profile(username: str, questionnaire_answers: dict) -> None:
    profiles_collection.update_one(
        {"username": username},
        {
            "$set": {
                "username": username,
                "questionnaire_answers": questionnaire_answers,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def get_user_profile(username: str) -> dict | None:
    return profiles_collection.find_one({"username": username})