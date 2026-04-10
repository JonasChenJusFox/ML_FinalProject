"""
frontend/ui.py
Owner: Jonas Chen

Responsibilities:
- Main frontend router for the Streamlit app
- Connects navigation state to page rendering
- Passes restaurant data into the correct view
- Stores frontend-ready data and filter options in session state
- Coordinates the overall UI flow of the application
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from frontend.adapters import get_filter_options
from frontend.components.nav import render_nav
from frontend.views.discover import render_discover
from frontend.views.home import render_home
from frontend.views.profile import render_profile
from frontend.views.wrapped import render_wrapped


PAGE_RENDERERS = {
    "Home": render_home,
    "Discover": render_discover,
    "Profile": render_profile,
    "Wrapped": render_wrapped,
}


def render_app(search_callable: Callable | None, preview_restaurants: list[dict]) -> None:
    st.session_state.preview_restaurants = (
        preview_restaurants or st.session_state.get("preview_restaurants", [])
    )
    st.session_state.filter_options = get_filter_options(st.session_state.preview_restaurants)

    current_page = render_nav()
    renderer = PAGE_RENDERERS.get(current_page, render_home)

    st.markdown("<div class='nb-shell'>", unsafe_allow_html=True)
    renderer(st.session_state.preview_restaurants)
    st.markdown("</div>", unsafe_allow_html=True)