"""
integration/account_service.py

Helpers for account deletion and personalization privacy actions.
"""

from __future__ import annotations

from integration.interaction_repo import delete_all_saved_restaurants_for_user
from integration.review_repo import (
    delete_all_reviews_for_user,
    exclude_user_reviews_from_personalization,
)
from integration.user_repo import (
    clear_user_profile,
    delete_user_by_username,
    find_user_by_username,
    set_personalization_state,
)
from integration.wrapped_repo import delete_all_interactions_for_user, empty_wrapped_stats


def clear_personalization_data(username: str) -> None:
    user = find_user_by_username(username) or {}
    personalization_enabled = bool(user.get("personalization_enabled", True))

    clear_user_profile(username)
    delete_all_interactions_for_user(username)
    delete_all_saved_restaurants_for_user(username)
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
    delete_all_reviews_for_user(username)
    delete_user_by_username(username)
