from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from PIL import Image
import streamlit as st

from frontend.state import init_state
from frontend.theme import apply_theme
from frontend.ui import render_app

try:
    from integration.api import search_restaurants as backend_search_restaurants
except Exception:
    backend_search_restaurants = None


ICON_PATH = Path("frontend/assets/nearbite.png")
FINAL_DATASET_PATH = Path("data/restaurants_with_google_reviews_final.json")

page_icon = Image.open(ICON_PATH) if ICON_PATH.exists() else "🍽️"

st.set_page_config(
    page_title="NearBite",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def load_preview_restaurants() -> list[dict]:
    if not FINAL_DATASET_PATH.exists():
        return []

    try:
        with FINAL_DATASET_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if isinstance(payload, list):
            return payload
    except Exception:
        return []

    return []


def main() -> None:
    apply_theme()

    preview_restaurants = load_preview_restaurants()
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