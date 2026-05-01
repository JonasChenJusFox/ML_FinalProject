"""Streamlit entrypoint: page config, theme, optional backend search, and :mod:`frontend.ui`."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image
import streamlit as st

from frontend.state import init_state
from frontend.theme import apply_theme
from frontend.ui import render_app

try:
    from integration.api import search_restaurants as backend_search_restaurants, get_all_restaurants
except Exception:
    backend_search_restaurants = None
    get_all_restaurants = None


ICON_PATH = Path("frontend/assets/nearbite.png")

page_icon = Image.open(ICON_PATH) if ICON_PATH.exists() else "🍽️"

st.set_page_config(
    page_title="NearBite",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    apply_theme()

    preview_restaurants = get_all_restaurants() if callable(get_all_restaurants) else []
    init_state(preview_restaurants)

    search_callable: Callable | None = (
        backend_search_restaurants if callable(backend_search_restaurants) else None
    )

    render_app(
        search_callable=search_callable,
        preview_restaurants=preview_restaurants,
    )


if __name__ == "__main__":
    main()