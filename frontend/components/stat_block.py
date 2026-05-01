"""Small labeled metric card used for dataset or user summary numbers."""

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