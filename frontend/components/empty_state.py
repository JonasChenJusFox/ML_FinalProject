"""Reusable empty-state panel (title + body) when lists or results are missing."""

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
