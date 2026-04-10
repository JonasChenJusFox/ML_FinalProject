"""
frontend/components/empty_state.py
Owner: Jonas Chen

Responsibilities:
- Renders reusable empty-state UI blocks
- Displays helpful messages when no restaurants or results are available
- Improves clarity and polish across pages with missing data
"""

from __future__ import annotations

import streamlit as st


def render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="nb-empty-state">
          <div class="nb-empty-title">{title}</div>
          <div class="nb-empty-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
