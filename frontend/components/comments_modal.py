"""
frontend/components/comments_modal.py
Owner: Jonas Chen

Responsibilities:
- Renders a single global comments modal
- Displays community reviews for the selected restaurant
- Lets logged-in users add or update a star rating and text review
- Keeps comment dialog state in Streamlit session state
"""

from __future__ import annotations

import html
import textwrap
from datetime import datetime

import streamlit as st

from frontend.adapters import clean_text
from frontend.auth import open_login_modal
from integration.review_repo import (
    get_reviews_for_restaurant,
    get_user_review,
    upsert_restaurant_review,
)
from integration.wrapped_repo import log_user_interaction


def _format_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%b %d, %Y")
        except ValueError:
            return value
    return ""


def init_comments_modal_state() -> None:
    if "show_comments_modal" not in st.session_state:
        st.session_state.show_comments_modal = False

    if "comments_modal_restaurant" not in st.session_state:
        st.session_state.comments_modal_restaurant = {}


def _format_rating(value: object) -> str:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        rating = 0.0
    return f"⭐ {rating:.1f}"


def _clear_comments_widget_state() -> None:
    active_business_id = clean_text(st.session_state.get("comments_modal_active_business_id", ""))
    for key in (
        "comments_modal_active_business_id",
        "comments_modal_login",
        "comments_modal_close",
    ):
        if key in st.session_state:
            del st.session_state[key]

    if active_business_id:
        for prefix in (
            "comments_modal_rating_",
            "comments_modal_comment_",
            "comments_modal_submit_",
        ):
            key = f"{prefix}{active_business_id}"
            if key in st.session_state:
                del st.session_state[key]


def open_comments_modal(restaurant: dict) -> None:
    _clear_comments_widget_state()
    st.session_state.show_login_modal = False
    st.session_state.show_signup_modal = False
    st.session_state.show_forgot_password_modal = False
    st.session_state.show_account_security_modal = False
    st.session_state.show_questionnaire_modal = False
    st.session_state.comments_modal_restaurant = dict(restaurant or {})
    st.session_state.show_comments_modal = True


def close_comments_modal() -> None:
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant = {}
    _clear_comments_widget_state()


def _render_community_reviews(business_id: str) -> None:
    reviews = get_reviews_for_restaurant(business_id)
    st.markdown("#### Community reviews")

    if not reviews:
        st.write("No community reviews yet.")
        return

    for idx, review in enumerate(reviews):
        display_name = clean_text(review.get("display_name") or review.get("username") or "User")
        rating = float(review.get("rating", 0.0) or 0.0)
        comment = clean_text(review.get("comment", ""))
        updated_label = _format_timestamp(review.get("updated_at"))

        safe_comment = html.escape(comment).replace("\n", "<br>")
        timestamp_html = f"<span class='nb-review-date'>{html.escape(updated_label)}</span>" if updated_label else ""

        st.markdown(
            textwrap.dedent(
                f"""
            <div class="nb-review-item">
              <div class="nb-review-head">
                <div class="nb-review-author">{html.escape(display_name)}</div>
                <div class="nb-review-rating">{html.escape(_format_rating(rating))}</div>
              </div>
              {timestamp_html}
              <div class="nb-comment-text">{safe_comment}</div>
            </div>
            """
            ).strip(),
            unsafe_allow_html=True,
        )

        if idx < len(reviews) - 1:
            st.divider()


def _render_source_reviews(source_reviews: list[dict] | list[str]) -> None:
    if not source_reviews:
        return

    st.markdown("#### Source review snippets")
    shown_any = False

    for idx, review in enumerate(source_reviews[:5], start=1):
        if isinstance(review, dict):
            text = clean_text(review.get("text", ""))
        else:
            text = clean_text(str(review))

        if not text:
            continue

        shown_any = True
        safe_text = html.escape(text).replace("\n", "<br>")
        st.markdown(
            f"<div class='nb-comment-text'><strong>Snippet {idx}.</strong> {safe_text}</div>",
            unsafe_allow_html=True,
        )
        if idx < min(len(source_reviews), 5):
            st.divider()

    if not shown_any:
        st.write("No source review snippets available.")


def _save_review(restaurant: dict, rating: float, comment: str) -> tuple[bool, str]:
    if not st.session_state.get("is_logged_in", False):
        return False, "Please log in before adding a review."

    current_user = st.session_state.get("current_user") or {}
    username = clean_text(current_user.get("username", ""))
    display_name = clean_text(current_user.get("display_name", username))
    business_id = clean_text(restaurant.get("business_id", ""))

    if not username or not business_id:
        return False, "We could not identify this review request."

    cleaned_comment = str(comment or "").strip()
    if not cleaned_comment:
        return False, "Please write a short review before saving."

    try:
        normalized_rating = round(float(rating), 1)
    except (TypeError, ValueError):
        return False, "Enter a valid rating between 0.0 and 5.0."

    if normalized_rating < 0.0 or normalized_rating > 5.0:
        return False, "Enter a valid rating between 0.0 and 5.0."

    upsert_restaurant_review(
        username=username,
        display_name=display_name,
        business_id=business_id,
        restaurant_name=clean_text(restaurant.get("name", "Restaurant")),
        restaurant_address=clean_text(restaurant.get("address", "")),
        restaurant_borough=clean_text(restaurant.get("borough", "")),
        restaurant_categories=list(restaurant.get("categories", [])),
        restaurant_price=clean_text(restaurant.get("price", "")),
        rating=normalized_rating,
        comment=cleaned_comment,
    )
    log_user_interaction(username, business_id, "reviewed")
    return True, "Your review has been saved."


def _render_review_form(restaurant: dict) -> None:
    st.markdown("#### Add your review")

    if not st.session_state.get("is_logged_in", False):
        st.info("Log in to add your own rating and review.")
        if st.button("Go to log in", key="comments_modal_login", use_container_width=True):
            close_comments_modal()
            open_login_modal()
            st.rerun()
        return

    st.markdown("<div class='nb-comments-form-anchor'></div>", unsafe_allow_html=True)

    current_user = st.session_state.get("current_user") or {}
    username = clean_text(current_user.get("username", ""))
    business_id = clean_text(restaurant.get("business_id", ""))
    existing_review = get_user_review(username, business_id) if username and business_id else None

    default_rating = float(existing_review.get("rating", 4.0) or 4.0) if existing_review else 4.0
    default_comment = clean_text(existing_review.get("comment", "")) if existing_review else ""

    rating_key = f"comments_modal_rating_{business_id}"
    comment_key = f"comments_modal_comment_{business_id}"
    marker_key = "comments_modal_active_business_id"
    if st.session_state.get(marker_key) != business_id:
        st.session_state[marker_key] = business_id
        st.session_state[rating_key] = round(max(0.0, min(5.0, default_rating)), 1)
        st.session_state[comment_key] = default_comment

    with st.form(f"comments_modal_review_form_{business_id}"):
        st.markdown("Your rating")
        rating_cols = st.columns([5.5, 0.7], gap="small")
        with rating_cols[0]:
            st.number_input(
                "Rating",
                min_value=0.0,
                max_value=5.0,
                step=0.1,
                format="%.1f",
                key=rating_key,
                label_visibility="collapsed",
            )
        with rating_cols[1]:
            st.markdown("<div class='nb-rating-input-icon'>⭐</div>", unsafe_allow_html=True)

        comment = st.text_area(
            "Your review",
            key=comment_key,
            placeholder="What did you like, and what would you order again?",
        )

        submitted = st.form_submit_button(
            "Update review" if existing_review else "Save review",
            key=f"comments_modal_submit_{business_id}",
            use_container_width=True,
        )

    if submitted:
        rating = float(st.session_state.get(rating_key, default_rating))
        comment = st.session_state.get(comment_key, "")
        success, message = _save_review(restaurant, float(rating), comment)
        if success:
            close_comments_modal()
            st.toast(message)
            st.rerun()
        st.error(message)


def render_comments_modal() -> None:
    init_comments_modal_state()

    if not st.session_state.get("show_comments_modal", False):
        return

    if any(
        [
            st.session_state.get("show_login_modal", False),
            st.session_state.get("show_signup_modal", False),
            st.session_state.get("show_forgot_password_modal", False),
        ]
    ):
        close_comments_modal()
        return

    @st.dialog("Comments")
    def _dialog() -> None:
        restaurant = st.session_state.get("comments_modal_restaurant", {}) or {}
        name = clean_text(restaurant.get("name", "Restaurant")) or "Restaurant"
        business_id = clean_text(restaurant.get("business_id", ""))
        source_reviews = restaurant.get("google_reviews", [])

        st.subheader(name)

        if business_id:
            _render_community_reviews(business_id)
            st.divider()
            _render_review_form(restaurant)
            if source_reviews:
                st.divider()
                _render_source_reviews(source_reviews)
        else:
            st.write("No review details are available for this restaurant.")

        if st.button("Close", key="comments_modal_close", use_container_width=True):
            close_comments_modal()
            st.rerun()

    _dialog()
    st.session_state.show_comments_modal = False
