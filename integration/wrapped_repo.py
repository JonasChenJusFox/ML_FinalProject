"""Build wrapped / recap statistics from saved places and interaction history in MongoDB."""

from __future__ import annotations

from integration.interaction_repo import (
    get_saved_restaurant_ids,
    get_user_interactions,
    upsert_user_interaction,
)


def log_user_interaction(
    username: str,
    business_id: str,
    action: str,
    review_signal: str | None = None,
    note: str | None = None,
) -> None:
    """
    Compatibility helper that only persists supported personalization actions.
    """
    if action not in {"save", "like", "review"}:
        return
    upsert_user_interaction(
        username=username,
        business_id=business_id,
        interaction_type=action,
        review_signal=review_signal,
        note=note,
    )


def build_wrapped_stats(username: str, restaurants: list[dict]) -> dict:
    """
    Build wrapped-style summary stats using normalized interaction history.
    """
    restaurant_index = {
        item.get("business_id"): item
        for item in restaurants
        if item.get("business_id")
    }

    saved_ids = get_saved_restaurant_ids(username)
    interactions = get_user_interactions(username)

    cuisine_counts: dict[str, int] = {}
    borough_counts: dict[str, int] = {}
    vibe_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}

    for business_id in saved_ids:
        restaurant = restaurant_index.get(business_id)
        if not restaurant:
            continue

        for category in restaurant.get("categories", [])[:3]:
            cuisine_counts[category] = cuisine_counts.get(category, 0) + 1

        borough = restaurant.get("borough")
        if borough:
            borough_counts[borough] = borough_counts.get(borough, 0) + 1

        for vibe in restaurant.get("vibes", []):
            vibe_counts[vibe] = vibe_counts.get(vibe, 0) + 1

    for interaction in interactions:
        action = interaction.get("interaction_type")
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1

    top_cuisines = sorted(cuisine_counts, key=cuisine_counts.get, reverse=True)[:3]
    top_boroughs = sorted(borough_counts, key=borough_counts.get, reverse=True)[:3]
    top_vibes = sorted(vibe_counts, key=vibe_counts.get, reverse=True)[:3]

    return {
        "saved_count": len(saved_ids),
        "interaction_count": len(interactions),
        "top_cuisines": top_cuisines,
        "top_boroughs": top_boroughs,
        "top_vibes": top_vibes,
        "action_counts": action_counts,
    }
