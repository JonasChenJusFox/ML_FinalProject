"""
frontend/components/restaurant_card.py
Owner: Jonas Chen

Responsibilities:
- Renders individual restaurant cards
- Displays image, cuisine, rating, address, and review snippet
- Handles save / unsave actions
- Supports focus-map behavior and comments dialog display
- Optionally links out to the restaurant source page
"""

from __future__ import annotations

import html

import streamlit as st

from frontend.adapters import clean_text, get_current_origin, shorten_text


@st.dialog("Comments")
def show_comments_dialog(name: str, reviews: list) -> None:
    st.subheader(name)

    if not reviews:
        st.write("No reviews available.")
        return

    shown_any = False
    for idx, review in enumerate(reviews, start=1):
        if isinstance(review, dict):
            text = clean_text(review.get("text", ""))
        else:
            text = clean_text(str(review))

        if text:
            shown_any = True
            st.markdown(f"**Comment {idx}**")
            safe_text = html.escape(text).replace("\n", "<br>")
            st.markdown(safe_text, unsafe_allow_html=True)
            if idx < len(reviews):
                st.divider()

    if not shown_any:
        st.write("No reviews available.")


def _get_price_for_card(restaurant: dict) -> str:
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
    price_text = _get_price_for_card(restaurant)
    borough = restaurant.get("borough", "Unknown")
    travel_minutes = restaurant.get("travel_minutes", "—")

    origin = get_current_origin()
    origin_label = origin.get("label", "NYU")

    meta_parts = []

    if price_text:
        meta_parts.append(price_text)

    if borough and borough != "Unknown":
        meta_parts.append(str(borough))

    if travel_minutes not in [None, "", 0, "—"]:
        meta_parts.append(f"{travel_minutes} min from {origin_label}")

    return " • ".join(meta_parts) if meta_parts else "Details not listed"


def render_restaurant_card(restaurant: dict, key_prefix: str = "card") -> None:
    business_id = restaurant.get("business_id", "")
    name = clean_text(restaurant.get("name", "Unknown"))
    categories = " · ".join(restaurant.get("categories", [])[:3]) or "Restaurant"
    rating = float(restaurant.get("rating", 0.0) or 0.0)
    address = clean_text(restaurant.get("address", "Address not listed")) or "Address not listed"
    review_text = shorten_text(restaurant.get("review_snippet", ""), 180)
    meta = _build_meta_line(restaurant)

    image_url = clean_text(restaurant.get("image_url", ""))
    if image_url:
        image_html = (
            f"<img src='{html.escape(image_url, quote=True)}' "
            f"alt='{html.escape(name, quote=True)}' class='nb-card-image'/>"
        )
    else:
        image_html = "<div class='nb-card-image nb-card-image-placeholder'></div>"

    st.markdown(
        f"""
        <div class="nb-card-wrap">
          <div class="nb-card">
            {image_html}
            <div class="nb-card-body">
              <div class="nb-card-head">
                <div>
                  <div class="nb-card-name">{html.escape(name)}</div>
                  <div class="nb-card-cuisine">{html.escape(categories)}</div>
                </div>
                <div class="nb-rating-pill">⭐ {rating:.1f}</div>
              </div>
              <div class="nb-card-meta">{html.escape(meta)}</div>
              <div class="nb-card-address">{html.escape(address)}</div>
              <div class="nb-card-review">{html.escape(review_text) if review_text else "No review snippet available."}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    saved_ids = st.session_state.get("saved_ids", []) or []
    already_saved = business_id in saved_ids

    row1 = st.columns(2, gap="small")
    row2 = st.columns(2, gap="small")

    if row1[0].button(
        "Unsave" if already_saved else "Save",
        key=f"{key_prefix}_save_{business_id}",
        use_container_width=True,
    ):
        if already_saved:
            st.session_state.saved_ids = [x for x in saved_ids if x != business_id]
        else:
            st.session_state.saved_ids = saved_ids + [business_id]
            st.toast("Saved!")
        st.rerun()

    if row1[1].button(
        "Focus map",
        key=f"{key_prefix}_focus_{business_id}",
        use_container_width=True,
    ):
        st.session_state.focus_business_id = business_id
        st.session_state.jump_to_business_id = business_id
        st.session_state.pending_discover_reset = True
        st.session_state.page = "Discover"
        st.rerun()

    if row2[0].button(
        "Comments",
        key=f"{key_prefix}_comments_{business_id}",
        use_container_width=True,
    ):
        show_comments_dialog(name, restaurant.get("google_reviews", []))

    url = clean_text(restaurant.get("url", ""))
    if url:
        row2[1].link_button("Source", url, use_container_width=True)
    else:
        row2[1].button(
            "No source",
            key=f"{key_prefix}_nosource_{business_id}",
            disabled=True,
            use_container_width=True,
        )