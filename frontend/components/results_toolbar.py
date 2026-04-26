"""
frontend/components/results_toolbar.py
Owner: Jonas Chen

Responsibilities:
- Renders the results toolbar above the restaurant list
- Displays result counts and view/display controls
- Supports options such as how many results to show at once
- Keeps result summary controls separate from the main Discover layout
"""

from __future__ import annotations

import streamlit as st


VIEW_OPTIONS = ["Grid", "List"]


def render_results_toolbar(result_count: int) -> str:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            f"""
            <div class="nb-toolbar">
              <div class="nb-toolbar-title">Discover</div>
              <div class="nb-toolbar-subtitle">{result_count} results matched your query and current filters.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        view_mode = st.radio(
            "View",
            options=VIEW_OPTIONS,
            horizontal=True,
            key="view_mode",
            label_visibility="collapsed",
        )
    return view_mode