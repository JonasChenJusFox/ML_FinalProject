"""
frontend/ui.py
Owner: Jonas Chen

Responsibilities:
- Main frontend router for the Streamlit app
- Connects navigation state to page rendering
- Passes restaurant data into the correct view
- Stores frontend-ready data and filter options in session state
- Coordinates the overall UI flow of the application
- Initializes authentication state and global modal rendering
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from frontend.adapters import get_filter_options
from frontend.auth import init_auth_state
from frontend.components.comments_modal import render_comments_modal
from frontend.components.forgot_password_modal import render_forgot_password_modal
from frontend.components.login_modal import render_login_modal
from frontend.components.nav import render_nav
from frontend.components.signup_modal import render_signup_modal
from frontend.views.discover import render_discover
from frontend.views.home import render_home
from frontend.views.profile import render_profile
from frontend.views.recommendation import render_recommendation

PAGE_RENDERERS = {
    "Home": render_home,
    "Discover": render_discover,
    "Profile": render_profile,
    "Recommendation": render_recommendation,
}


def render_app(search_callable: Callable | None, preview_restaurants: list[dict]) -> None:
    """
    Render the main application shell and route the user
    to the currently selected page.
    """
    init_auth_state()

    st.session_state.preview_restaurants = (
        preview_restaurants or st.session_state.get("preview_restaurants", [])
    )
    st.session_state.filter_options = get_filter_options(
        st.session_state.preview_restaurants
    )

    # Global modals
    render_login_modal()
    render_signup_modal()
    render_forgot_password_modal()
    render_comments_modal()

    current_page = render_nav()
    renderer = PAGE_RENDERERS.get(current_page, render_home)

    st.markdown("<div class='nb-shell'>", unsafe_allow_html=True)
    renderer(st.session_state.preview_restaurants)
    st.markdown("</div>", unsafe_allow_html=True)