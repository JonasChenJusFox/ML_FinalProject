"""
frontend/components/stat_block.py
Owner: Jonas Chen

Responsibilities:
- Renders small summary statistic blocks across the app
- Displays values such as dataset size, saved places, or average rating
- Provides a consistent visual format for compact metrics
- Helps keep repeated stat-card markup reusable
"""

from __future__ import annotations

import streamlit as st


def render_stat_block(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="nb-stat-card">
          <div class="nb-stat-value">{value}</div>
          <div class="nb-stat-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )