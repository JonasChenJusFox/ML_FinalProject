"""
frontend/views/profile.py
Owner: Jonas Chen

Responsibilities:
- Renders the combined profile page
- Displays wrapped summary and saved restaurants
- Shows a dedicated reviewed-restaurants section with the user's own review text
"""

from __future__ import annotations

import html
import textwrap
from datetime import datetime

import streamlit as st

from frontend.adapters import clean_text, normalize_results
from frontend.auth import open_login_modal
from frontend.components.empty_state import render_empty_state
from frontend.components.restaurant_card import render_restaurant_card
from integration.api import get_restaurants_by_ids
from integration.review_repo import get_user_reviews
from integration.wrapped_repo import build_wrapped_stats


def _init_profile_state() -> None:
    if "profile_show_reviews" not in st.session_state:
        st.session_state.profile_show_reviews = False


def _format_review_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%b %d, %Y")
        except ValueError:
            return value
    return ""


def _render_user_review_history(reviews: list[dict], restaurant_index: dict[str, dict]) -> None:
    st.markdown(
        "<div class='nb-section-title'>Your reviews</div>",
        unsafe_allow_html=True,
    )

    if not reviews:
        render_empty_state(
            "No reviews yet",
            "Add a comment from any restaurant card and it will show up here.",
        )
        return

    for review in reviews:
        business_id = clean_text(review.get("business_id", ""))
        restaurant = restaurant_index.get(business_id, {})
        name = clean_text(review.get("restaurant_name") or restaurant.get("name") or "Restaurant")
        borough = clean_text(review.get("restaurant_borough") or restaurant.get("borough") or "")
        address = clean_text(review.get("restaurant_address") or restaurant.get("address") or "")
        rating = float(review.get("rating", 0.0) or 0.0)
        comment = clean_text(review.get("comment", ""))
        updated_at = _format_review_timestamp(review.get("updated_at"))

        meta_parts = [item for item in [borough, updated_at] if item]
        meta = " • ".join(meta_parts)
        safe_comment = html.escape(comment).replace("\n", "<br>")

        st.markdown(
            textwrap.dedent(
                f"""
                <div class="nb-wrap-restaurant">
                  <div class="nb-wrap-restaurant-name">{html.escape(name)}</div>
                  <div class="nb-wrap-restaurant-meta">{html.escape(meta)}</div>
                  <div class="nb-card-address">{html.escape(address)}</div>
                  <div class="nb-review-rating">{html.escape(f"⭐ {rating:.1f}")}</div>
                  <div class="nb-comment-text">{safe_comment}</div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )


def render_profile(restaurants: list[dict]) -> None:
    """
    Render the Profile page with wrapped summary, saved restaurants, and reviews.
    """
    _init_profile_state()
    st.markdown("### Profile")

    if not st.session_state.get("is_logged_in", False):
        st.info("Please log in to view your profile, reviews, and saved restaurants.")
        if st.button("Log in", key="profile_login_button"):
            open_login_modal()
            st.rerun()
        return

    current_user = st.session_state.get("current_user", {})
    username = current_user.get("username", "")

    if not username:
        st.info("Please log in to view your profile, reviews, and saved restaurants.")
        if st.button("Log in", key="profile_login_button_fallback"):
            open_login_modal()
            st.rerun()
        return

    reviews = get_user_reviews(username)
    saved_ids = st.session_state.get("saved_ids", []) or []
    review_business_ids = [
        clean_text(review.get("business_id", ""))
        for review in reviews
        if clean_text(review.get("business_id", ""))
    ]
    extra_restaurants = get_restaurants_by_ids(saved_ids + review_business_ids)
    combined_restaurants = list(restaurants or []) + extra_restaurants
    normalized = normalize_results(combined_restaurants)
    restaurant_index = {
        item.get("business_id"): item
        for item in normalized
        if item.get("business_id")
    }

    saved_restaurants = [restaurant_index[item_id] for item_id in saved_ids if item_id in restaurant_index]
    wrapped = build_wrapped_stats(username, normalized)

    st.markdown(
        "<div class='nb-section-title'>Wrapped summary</div>",
        unsafe_allow_html=True,
    )

    summary_cols = st.columns(4, gap="small")

    summary_cols[0].markdown(
        f"""
        <div class="nb-wrap-card">
          <div class="nb-panel-title">Saved places</div>
          <div class="nb-wrap-value">{wrapped.get('saved_count', 0)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_cuisine = ", ".join(wrapped.get("top_cuisines", [])[:2]) or "Not enough data yet"
    summary_cols[1].markdown(
        f"""
        <div class="nb-wrap-card">
          <div class="nb-panel-title">Top cuisine</div>
          <div class="nb-wrap-value">{top_cuisine}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_borough = ", ".join(wrapped.get("top_boroughs", [])[:2]) or "Not enough data yet"
    summary_cols[2].markdown(
        f"""
        <div class="nb-wrap-card">
          <div class="nb-panel-title">Top borough</div>
          <div class="nb-wrap-value">{top_borough}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    reviewed_count = wrapped.get("reviewed_count", 0)
    summary_cols[3].markdown(
        f"""
        <div class="nb-wrap-card">
          <div class="nb-panel-title">Reviewed places</div>
          <div class="nb-wrap-value">{reviewed_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    review_button_label = "Hide reviews" if st.session_state.get("profile_show_reviews", False) else "Reviews"
    if st.button(review_button_label, key="profile_reviews_button", use_container_width=True):
        st.session_state.profile_show_reviews = not st.session_state.get("profile_show_reviews", False)
        st.rerun()

    if st.session_state.get("profile_show_reviews", False):
        _render_user_review_history(reviews, restaurant_index)

    st.markdown(
        "<div class='nb-section-title'>Saved restaurants</div>",
        unsafe_allow_html=True,
    )
    st.caption("Use Focus map to jump to Discover and move that restaurant to the top.")

    if not saved_restaurants:
        render_empty_state(
            "Nothing saved yet",
            "Save a few restaurants from Discover and they will appear here.",
        )
        return

    for idx, item in enumerate(saved_restaurants):
        render_restaurant_card(item, key_prefix=f"profile_saved_{idx}")
