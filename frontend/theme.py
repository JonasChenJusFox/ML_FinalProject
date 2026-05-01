"""Load NearBite assets and inject global Streamlit CSS for consistent layout and branding."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

FRONTEND_DIR = Path(__file__).resolve().parent
ASSETS_DIR = FRONTEND_DIR / "assets"


def asset_path(filename: str) -> Path:
    return ASSETS_DIR / filename


def asset_to_data_uri(filename: str, mime_type: str) -> str:
    path = asset_path(filename)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def apply_theme() -> None:
    css_path = asset_path("custom.css")
    if not css_path.exists():
        st.warning("frontend/assets/custom.css not found.")
        return

    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)