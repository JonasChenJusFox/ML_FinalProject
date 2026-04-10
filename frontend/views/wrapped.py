"""
frontend/views/wrapped.py
Owner: Jonas Chen

Responsibilities:
- Renders the NearBite recap / wrapped page
- Displays summary metrics from saved and viewed restaurants
- Shows top cuisines, explored boroughs, and related recap content
- Presents a simple session-based restaurant activity summary
"""

from __future__ import annotations

import streamlit as st

from frontend.adapters import get_wrapped_summary, normalize_results
from frontend.components.empty_state import render_empty_state
from frontend.components.wrapped_card import render_wrapped_card


def render_wrapped(restaurants: list[dict]) -> None:
    summary = get_wrapped_summary(restaurants, st.session_state.saved_ids, st.session_state.viewed_ids)
    normalized = normalize_results(restaurants)
    index = {item["business_id"]: item for item in normalized}

    if summary["top_cuisine"] == "No data yet":
        render_empty_state(
            "Not enough activity yet",
            "Explore restaurants, focus a few on the map, and save favorites to generate your recap.",
        )
        return

    st.markdown("<div class='nb-section-title'>Your NearBite recap</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        render_wrapped_card("Top cuisine", summary["top_cuisine"])
    with cols[1]:
        render_wrapped_card("Most explored borough", summary["top_borough"])
    with cols[2]:
        render_wrapped_card("Average price", summary["avg_price"])
    with cols[3]:
        render_wrapped_card("New cuisines tried", str(summary["new_cuisines"]))

    st.markdown("<div class='nb-section-title'>Top restaurants</div>", unsafe_allow_html=True)

    ordered_ids = []
    for item_id in st.session_state.viewed_ids + st.session_state.saved_ids:
        if item_id in index and item_id not in ordered_ids:
            ordered_ids.append(item_id)

    for item_id in ordered_ids[:5]:
        item = index[item_id]
        st.markdown(
            f"""
            <div class="nb-wrap-restaurant">
              <div class="nb-wrap-restaurant-name">{item['name']}</div>
              <div class="nb-wrap-restaurant-meta">
                {' · '.join(item.get('categories', [])[:3]) or 'Restaurant'} ·
                {item.get('borough', 'Unknown')} ·
                ⭐ {item.get('rating', 0.0):.1f} ·
                {item.get('price_display', '—')}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )