"""Restaurant card: media, metadata, save/like/review with auth gating, map focus, and comments."""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components

from frontend.adapters import clean_text, get_current_origin, shorten_text
from frontend.auth import open_login_modal
from frontend.components.comments_modal import open_comments_modal
from integration.interaction_repo import (
    get_liked_restaurant_ids,
    get_saved_restaurant_ids,
    get_user_interaction_map,
    like_restaurant_for_user,
    review_restaurant_for_user,
    save_restaurant_for_user,
    unlike_restaurant_for_user,
    unsave_restaurant_for_user,
)

REVIEW_OPTIONS = ["love", "neutral", "hate"]

# Display-only: backend / ranker may still use semantic labels on ``price`` fields.
_SEMANTIC_PRICE_TO_DOLLARS: dict[str, str] = {
    "cheap": "$",
    "budget": "$",
    "affordable": "$",
    "moderate": "$$",
    "mid range": "$$",
    "midrange": "$$",
    "expensive": "$$$",
    "upscale": "$$$",
    "luxury": "$$$$",
    "unknown": "",
}


def _format_price_for_ui(label: str) -> str:
    """Turn semantic price words into ``$`` tiers for the card only; leave other labels as-is."""
    text = (label or "").strip()
    if not text:
        return ""
    if text.replace("$", "").strip() == "":
        return text
    key = text.lower().replace("-", " ").strip()
    return _SEMANTIC_PRICE_TO_DOLLARS.get(key, text)


# Injected into components.html iframe so card layout matches main app CSS.
_CARD_IFRAME_STYLES = """
<style>
  .nb-card-wrap { margin-bottom: 0.9rem; }
  .nb-card {
    overflow: hidden;
    background: #fffdf9;
    border: 1px solid #ddd4c9;
    box-shadow: 0 10px 24px rgba(31, 28, 25, 0.06);
    font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1f1c19;
  }
  .nb-card-image,
  .nb-card-image-placeholder {
    width: 100%;
    height: 240px;
    object-fit: cover;
    object-position: center;
    display: block;
    background: linear-gradient(180deg, #ebe2d8 0%, #ddd2c8 100%);
  }
  .nb-card-image-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #7d746b;
  }
  .nb-card-image-fallback { font-size: 0.95rem; }
  .nb-card-body { padding: 1rem; }
  .nb-card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }
  .nb-card-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1f1c19;
    margin-bottom: 0.22rem;
    line-height: 1.25;
  }
  .nb-card-cuisine,
  .nb-card-meta,
  .nb-card-address,
  .nb-card-review { color: #6a6158; }
  .nb-card-meta { margin: 0.72rem 0 0.46rem 0; font-size: 0.95rem; }
  .nb-card-address { font-size: 0.92rem; margin-bottom: 0.55rem; line-height: 1.5; }
  .nb-card-review {
    line-height: 1.72;
    font-size: 0.96rem;
    border-top: 1px solid #eee5db;
    padding-top: 0.75rem;
    min-height: 5.1rem;
  }
  .nb-rating-pill {
    border: 1px solid #e5cabd;
    background: #fff0eb;
    color: #d96558;
    font-weight: 700;
    padding: 0.42rem 0.66rem;
    white-space: nowrap;
    min-width: 72px;
    text-align: center;
  }
</style>
"""


def _get_price_for_card(restaurant: dict) -> str:
    """
    Resolve the best available price label for display on the card.
    """
    missing_labels = {
        "unknown",
        "n/a",
        "na",
        "none",
        "null",
        "not available",
        "price not listed",
    }

    price_display = clean_text(restaurant.get("price_display", ""))
    if price_display and price_display.lower() not in missing_labels:
        return _format_price_for_ui(price_display)

    price = clean_text(restaurant.get("price", ""))
    if price and price.lower() not in missing_labels:
        return _format_price_for_ui(price)

    price_original = clean_text(restaurant.get("price_original", ""))
    if price_original and price_original.lower() not in missing_labels:
        return _format_price_for_ui(price_original)

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
    borough = restaurant.get("borough", "Unknown")
    travel_minutes = restaurant.get("travel_minutes", "—")

    origin = get_current_origin()
    origin_label = origin.get("label", "NYU")

    meta_parts: list[str] = []

    if price_text:
        meta_parts.append(price_text)

    if borough and borough != "Unknown":
        meta_parts.append(str(borough))

    if travel_minutes not in [None, "", 0, "—"]:
        meta_parts.append(f"{travel_minutes} min from {origin_label}")

    return " • ".join(meta_parts) if meta_parts else "Details not listed"


def _require_logged_in_user() -> str | None:
    if not st.session_state.get("is_logged_in", False):
        open_login_modal()
        st.rerun()

    current_user = st.session_state.get("current_user")
    username = current_user.get("username") if current_user else None
    if not username:
        open_login_modal()
        st.rerun()
    return username


def _refresh_user_interaction_state(username: str) -> None:
    st.session_state.saved_ids = get_saved_restaurant_ids(username)
    st.session_state.liked_ids = get_liked_restaurant_ids(username)
    st.session_state.interaction_map = get_user_interaction_map(username)


def _handle_save_toggle(business_id: str, already_saved: bool) -> None:
    username = _require_logged_in_user()
    if not username:
        return

    if already_saved:
        unsave_restaurant_for_user(username, business_id)
        st.toast("Removed from saved restaurants.")
    else:
        save_restaurant_for_user(username, business_id)
        st.toast("Saved.")

    _refresh_user_interaction_state(username)
    st.rerun()


def _handle_like_toggle(business_id: str, already_liked: bool) -> None:
    username = _require_logged_in_user()
    if not username:
        return

    if already_liked:
        unlike_restaurant_for_user(username, business_id)
        st.toast("Like removed.")
    else:
        like_restaurant_for_user(username, business_id)
        st.toast("Liked.")

    _refresh_user_interaction_state(username)
    st.rerun()


def _handle_review_submit(
    business_id: str,
    review_signal: str,
    note: str,
) -> None:
    username = _require_logged_in_user()
    if not username:
        return

    review_restaurant_for_user(
        username=username,
        business_id=business_id,
        review_signal=review_signal,
        note=note,
    )
    _refresh_user_interaction_state(username)
    st.toast("Your review was saved.")
    st.rerun()


def _toggle_review_editor(card_key: str) -> None:
    review_state_key = f"{card_key}_review_open"
    st.session_state[review_state_key] = not st.session_state.get(review_state_key, False)


def _handle_focus_map(business_id: str) -> None:
    """
    Move the selected restaurant into focus on the Discover page map.
    """
    st.session_state.focus_business_id = business_id
    st.session_state.jump_to_business_id = business_id
    st.session_state.page = "Discover"
    st.rerun()


def _render_user_record(record: dict | None) -> None:
    if not record:
        return

    status_parts: list[str] = []
    if record.get("saved"):
        status_parts.append("saved")
    if record.get("liked"):
        status_parts.append("liked")
    review_signal = record.get("review_signal")
    if review_signal:
        status_parts.append(f"review: {review_signal}")

    if status_parts:
        st.caption("Your record: " + " • ".join(status_parts))

    note = str(record.get("note") or "").strip()
    if note:
        st.caption(f"Private note: {note}")


def render_restaurant_card(restaurant: dict, key_prefix: str = "card") -> None:
    """
    Render a single restaurant card and its action buttons.
    """
    business_id = restaurant.get("business_id", "")
    name = clean_text(restaurant.get("name", "Unknown"))
    raw_categories = restaurant.get("categories", [])
    if not isinstance(raw_categories, list):
        raw_categories = [raw_categories] if raw_categories else []
    categories = " · ".join(clean_text(item) for item in raw_categories[:3] if clean_text(item)) or "Restaurant"
    rating = float(restaurant.get("rating", 0.0) or 0.0)
    address = clean_text(restaurant.get("address", ""))
    review_text = shorten_text(restaurant.get("review_snippet", ""), 180)
    meta = _build_meta_line(restaurant)

    image_url = clean_text(restaurant.get("image_url", ""))
    if image_url:
        image_html = (
            f"<img src='{html.escape(image_url, quote=True)}' "
            f"alt='{html.escape(name, quote=True)}' class='nb-card-image'/>"
        )
    else:
        image_html = (
            "<div class='nb-card-image nb-card-image-placeholder'>"
            "<div class='nb-card-image-fallback'>Image unavailable</div></div>"
        )

    # components.html bypasses Markdown; st.markdown can still surface HTML as plain text
    # for some payloads (e.g. review text with Markdown-like characters).
    address_display = html.escape(address) if address else "Address not listed"
    review_display = (
        html.escape(review_text) if review_text else "No review snippet available."
    )
    card_inner = (
        f'<div class="nb-card-wrap"><div class="nb-card">{image_html}'
        f'<div class="nb-card-body"><div class="nb-card-head"><div>'
        f'<div class="nb-card-name">{html.escape(name)}</div>'
        f'<div class="nb-card-cuisine">{html.escape(categories)}</div></div>'
        f'<div class="nb-rating-pill">⭐ {rating:.1f}</div></div>'
        f'<div class="nb-card-meta">{html.escape(meta)}</div>'
        f'<div class="nb-card-address">{address_display}</div>'
        f'<div class="nb-card-review">{review_display}</div>'
        f"</div></div></div>"
    )
    components.html(
        _CARD_IFRAME_STYLES + card_inner,
        height=380,
        scrolling=False,
    )

    # Keep card height stable, but let users reveal long addresses on demand.
    if address and len(address) > 70:
        with st.expander("Show full address"):
            st.caption(address)

    interaction_map = st.session_state.get("interaction_map", {}) or {}
    record = interaction_map.get(business_id, {})
    _render_user_record(record)

    saved_ids = st.session_state.get("saved_ids", []) or []
    liked_ids = st.session_state.get("liked_ids", []) or []
    already_saved = business_id in saved_ids
    already_liked = business_id in liked_ids

    row1 = st.columns(3, gap="small")
    row2 = st.columns(2, gap="small")

    if row1[0].button(
        "Unsave" if already_saved else "Save",
        key=f"{key_prefix}_save_{business_id}",
        use_container_width=True,
    ):
        _handle_save_toggle(business_id, already_saved)

    if row1[1].button(
        "Unlike" if already_liked else "Like",
        key=f"{key_prefix}_like_{business_id}",
        use_container_width=True,
    ):
        _handle_like_toggle(business_id, already_liked)

    if row1[2].button(
        "Review",
        key=f"{key_prefix}_review_toggle_{business_id}",
        use_container_width=True,
    ):
        if not st.session_state.get("is_logged_in", False):
            open_login_modal()
            st.rerun()
        _toggle_review_editor(f"{key_prefix}_{business_id}")

    if row2[0].button(
        "Focus Map",
        key=f"{key_prefix}_focus_{business_id}",
        use_container_width=True,
    ):
        _handle_focus_map(business_id)

    if row2[1].button(
        "Comments",
        key=f"{key_prefix}_comments_{business_id}",
        use_container_width=True,
    ):
        open_comments_modal(name, restaurant.get("google_reviews", []))
        st.rerun()

    review_open = st.session_state.get(f"{key_prefix}_{business_id}_review_open", False)
    if review_open:
        st.caption("Your private review is used only for your own history and interaction-based personalization.")
        current_review_signal = record.get("review_signal")
        default_review_index = (
            REVIEW_OPTIONS.index(current_review_signal)
            if current_review_signal in REVIEW_OPTIONS
            else 0
        )
        review_signal = st.selectbox(
            "Review",
            options=REVIEW_OPTIONS,
            index=default_review_index,
            key=f"{key_prefix}_review_signal_{business_id}",
        )
        note_value = st.text_area(
            "Private note (optional)",
            value=str(record.get("note") or ""),
            key=f"{key_prefix}_review_note_{business_id}",
            height=80,
            placeholder="Only visible on your profile. This note is not used for recommendations.",
        )
        if st.button(
            "Save review",
            key=f"{key_prefix}_save_review_{business_id}",
            use_container_width=True,
        ):
            _handle_review_submit(
                business_id=business_id,
                review_signal=review_signal,
                note=note_value,
            )
        if st.button(
            "Close review",
            key=f"{key_prefix}_close_review_{business_id}",
            use_container_width=True,
        ):
            st.session_state[f"{key_prefix}_{business_id}_review_open"] = False
            st.rerun()
