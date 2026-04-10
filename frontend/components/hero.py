"""
frontend/components/hero.py
Owner: Jonas Chen

Responsibilities:
- Renders the homepage hero section
- Displays the main marketing message and search-oriented introduction
- Supports branded visual presentation for the landing area
"""

from __future__ import annotations

import streamlit as st

from frontend.theme import asset_to_data_uri


def render_home_hero() -> None:

    st.markdown(
        f"""
        <section class="nb-hero-html">
          <div class="nb-hero-inner">
            <div class="nb-hero-kicker">NearBite</div>
            <h1 class="nb-hero-title">Looking for great food nearby? Just use NearBite.</h1>
            <p class="nb-hero-copy">
              Search the way people actually search: cozy date spots in Manhattan,
              strong noodles near NYU, or a place that fits tonight.
            </p>
            <div class="nb-hero-tags">
              <span>Thai</span>
              <span>Japanese</span>
              <span>Chinese</span>
              <span>25 min radius</span>
              <span>Personalized feed</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )