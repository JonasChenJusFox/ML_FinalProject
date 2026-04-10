"""
frontend/components/wrapped_card.py
Owner: Jonas Chen

Responsibilities:
- Renders summary cards on the Wrapped page
- Displays recap metrics in a clean and consistent format
- Supports the session-based NearBite recap experience
"""

from __future__ import annotations

import streamlit as st


def render_wrapped_card(title: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="nb-wrap-card">
          <div class="nb-panel-title">{title}</div>
          <div class="nb-wrap-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )