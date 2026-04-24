"""
frontend/components/restaurant_card.py
Owner: Jonas Chen

Responsibilities:
- Renders individual restaurant cards
- Displays image, cuisine, rating, address, and review snippet
- Handles save / unsave actions with login gating
- Writes saved restaurant state to MongoDB for logged-in users
- Logs wrapped-related interaction events to MongoDB
- Supports focus-map behavior and comments dialog display
- Optionally links out to the restaurant source page
"""

from __future__ import annotations

import html

import streamlit as st

from frontend.adapters import clean_text, get_current_origin, shorten_text
from frontend.auth import open_login_modal
from frontend.components.comments_modal import open_comments_modal
from integration.db import (
    get_liked_restaurant_ids,
    get_saved_restaurant_ids,
    like_restaurant_for_user,
    log_user_interaction,
    save_restaurant_for_user,
    unlike_restaurant_for_user,
    unsave_restaurant_for_user,
)

MISSING_TEXT_VALUES = {
    "",
    "unknown",
    "details not listed",
    "address not listed",
    "no description available.",
    "restaurant",
}


def _get_price_for_card(restaurant: dict) -> str:
    """
    Resolve the best available price label for display on the card.
    """
    price_display = clean_text(restaurant.get("price_display", ""))
    if price_display and price_display != "Price not listed":
        return price_display

    price = clean_text(restaurant.get("price", ""))
    if price:
        return price

    price_original = clean_text(restaurant.get("price_original", ""))
    if price_original:
        return price_original

    try:
        price_level = int(restaurant.get("price_level", 0) or 0)
    except (TypeError, ValueError):
        price_level = 0

    if price_level > 0:
        return "$" * price_level

    return ""


def _build_meta_line(restaurant: dict) -> str:
    """
    Build the short metadata line shown under the restaurant title.
    """
    price_text = _get_price_for_card(restaurant)
    borough = clean_text(restaurant.get("borough", ""))
    travel_minutes = restaurant.get("travel_minutes", "—")

    origin = get_current_origin()
    origin_label = origin.get("travel_label") or origin.get("label") or "Current location"

    meta_parts: list[str] = []

    if price_text:
        meta_parts.append(price_text)

    if borough and borough.lower() not in MISSING_TEXT_VALUES:
        meta_parts.append(str(borough))

    if travel_minutes not in [None, "", 0, "—"]:
        meta_parts.append(f"{travel_minutes} min from {origin_label}")

    return " • ".join(meta_parts)


def _log_if_logged_in(business_id: str, action: str) -> None:
    """
    Log an interaction only if the current user is logged in.
    """
    if not st.session_state.get("is_logged_in", False):
        return

    current_user = st.session_state.get("current_user")
    username = current_user.get("username") if current_user else None
    if not username:
        return

    log_user_interaction(username, business_id, action)


def _require_login_for_interaction() -> str | None:
    if not st.session_state.get("is_logged_in", False):
        open_login_modal()
        st.rerun()

    current_user = st.session_state.get("current_user")
    username = current_user.get("username") if current_user else None
    if not username:
        open_login_modal()
        st.rerun()

    return username


def _handle_save_toggle(business_id: str, already_saved: bool, saved_ids: list[str]) -> None:
    """
    Save or unsave a restaurant.
    If the user is not logged in, open the login modal instead.
    """
    username = _require_login_for_interaction()
    if not username:
        return

    if already_saved:
        unsave_restaurant_for_user(username, business_id)
        _log_if_logged_in(business_id, "unsaved")
        st.toast("Removed from saved restaurants.")
    else:
        save_restaurant_for_user(username, business_id)
        _log_if_logged_in(business_id, "saved")
        st.toast("Saved!")

    st.session_state.saved_ids = get_saved_restaurant_ids(username)
    st.rerun()


def _handle_like_toggle(business_id: str, already_liked: bool, liked_ids: list[str]) -> None:
    username = _require_login_for_interaction()
    if not username:
        return

    if already_liked:
        unlike_restaurant_for_user(username, business_id)
        _log_if_logged_in(business_id, "unliked")
        st.toast("Removed from likes.")
    else:
        like_restaurant_for_user(username, business_id)
        _log_if_logged_in(business_id, "liked")
        st.toast("Liked!")

    st.session_state.liked_ids = get_liked_restaurant_ids(username)
    st.rerun()


def _handle_focus_map(business_id: str) -> None:
    """
    Move the selected restaurant into focus on the Discover page map.
    """
    _log_if_logged_in(business_id, "focus_map")

    st.session_state.focus_business_id = business_id
    st.session_state.jump_to_business_id = business_id
    st.session_state.page = "Discover"
    st.rerun()


def _handle_open_comments(restaurant: dict) -> None:
    business_id = clean_text(restaurant.get("business_id", ""))
    open_comments_modal(restaurant)
    if business_id:
        _log_if_logged_in(business_id, "comments_opened")


def render_restaurant_card(restaurant: dict, key_prefix: str = "card") -> None:
    """
    Render a single restaurant card and its action buttons.
    """
    business_id = restaurant.get("business_id", "")
    name = clean_text(restaurant.get("name", "Unknown"))
    category_values = [
        clean_text(category)
        for category in restaurant.get("categories", [])[:3]
        if clean_text(category).lower() not in MISSING_TEXT_VALUES
    ]
    categories = " · ".join(category_values[:2])
    rating = float(restaurant.get("rating", 0.0) or 0.0)
    address = clean_text(restaurant.get("address", ""))
    body_text = shorten_text(
        restaurant.get("description") or restaurant.get("review_snippet", ""),
        220,
    )
    meta = _build_meta_line(restaurant)
    url = clean_text(restaurant.get("url", ""))

    image_url = clean_text(restaurant.get("image_url", ""))
    if image_url:
        image_html = (
            f"<img src='{html.escape(image_url, quote=True)}' "
            f"alt='{html.escape(name, quote=True)}' class='nb-card-image'/>"
        )
    else:
        image_html = (
            "<div class='nb-card-image nb-card-image-placeholder'>"
            "<div class='nb-card-image-fallback'>Image unavailable</div>"
            "</div>"
        )

    footer_link_html = ""
    if url:
        footer_link_html = (
            f"<div class='nb-card-link'><a href='{html.escape(url, quote=True)}' "
            f"target='_blank' rel='noopener noreferrer'>Visit listing</a></div>"
        )

    card_html_parts = [
        '<div class="nb-card-wrap">',
        '<div class="nb-card">',
        image_html.strip(),
        '<div class="nb-card-body">',
        '<div class="nb-card-head">',
        "<div>",
        f'<div class="nb-card-name">{html.escape(name)}</div>',
        (f'<div class="nb-card-cuisine">{html.escape(categories)}</div>' if categories else ""),
        "</div>",
        f'<div class="nb-rating-pill">⭐ {rating:.1f}</div>',
        "</div>",
        (f'<div class="nb-card-meta">{html.escape(meta)}</div>' if meta else ""),
        (f'<div class="nb-card-address">{html.escape(address)}</div>' if address else ""),
        (
            "<div class='nb-card-review'>"
            f"{html.escape(body_text)}"
            "</div>"
            if body_text and body_text.lower() not in MISSING_TEXT_VALUES
            else ""
        ),
    ]
    if footer_link_html:
        card_html_parts.append(footer_link_html)
    card_html_parts.extend(
        [
            "</div>",
            "</div>",
            "</div>",
        ]
    )

    st.markdown("\n".join(card_html_parts), unsafe_allow_html=True)

    saved_ids = st.session_state.get("saved_ids", []) or []
    liked_ids = st.session_state.get("liked_ids", []) or []
    already_saved = business_id in saved_ids
    already_liked = business_id in liked_ids

    row1 = st.columns(3, gap="small")

    if row1[0].button(
        "Unlike" if already_liked else "Like",
        key=f"{key_prefix}_like_{business_id}",
        use_container_width=True,
    ):
        _handle_like_toggle(business_id, already_liked, liked_ids)

    if row1[1].button(
        "Unsave" if already_saved else "Save",
        key=f"{key_prefix}_save_{business_id}",
        use_container_width=True,
    ):
        _handle_save_toggle(business_id, already_saved, saved_ids)

    if row1[2].button(
        "Focus map",
        key=f"{key_prefix}_focus_{business_id}",
        use_container_width=True,
    ):
        _handle_focus_map(business_id)

    st.button(
        "Review",
        key=f"{key_prefix}_comments_{business_id}",
        use_container_width=True,
        on_click=_handle_open_comments,
        args=(restaurant,),
    )
