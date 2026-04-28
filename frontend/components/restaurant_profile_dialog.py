"""
frontend/components/restaurant_profile_dialog.py

Responsibilities:
- Shows a full restaurant card in a dialog (e.g. after a map marker click)
"""

from __future__ import annotations

import streamlit as st

from frontend.components.dialog_gate import can_open_dialog
from frontend.components.map_view import clear_discover_map_pin_selection
from frontend.components.restaurant_card import render_restaurant_card


def render_restaurant_profile_dialog(restaurants: list[dict]) -> None:
    business_id = st.session_state.get("restaurant_profile_business_id")
    if not business_id:
        return
    if not can_open_dialog("restaurant_profile_dialog"):
        return

    item = next((r for r in restaurants if r.get("business_id") == business_id), None)
    if not item:
        clear_discover_map_pin_selection()
        return

    title = str(item.get("name") or "Restaurant")

    @st.dialog(title, on_dismiss=lambda: clear_discover_map_pin_selection())
    def _dialog() -> None:
        render_restaurant_card(item, key_prefix="map_profile_dialog")

    _dialog()
