"""Styled recap metric tile for wrapped-style summaries on the profile page."""

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