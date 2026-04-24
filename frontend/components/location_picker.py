"""
frontend/components/location_picker.py
Owner: Jonas Chen

Responsibilities:
- Renders the Discover-page current-origin summary below the search bar
- Renders ZIP selection controls inside the filter panel
- Supports browser geolocation without exposing the raw GPS icon widget
- Applies frontend-only origin changes for travel-time display and map centering
"""

from __future__ import annotations

import html
import textwrap
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from streamlit_geolocation import streamlit_geolocation

from frontend.adapters import (
    clear_user_origin,
    get_current_origin,
    set_user_origin,
)
from frontend.location_utils import (
    get_supported_zipcode_options,
    resolve_zipcode_location,
)


def _ensure_location_state() -> None:
    if "location_zipcode_input" not in st.session_state:
        st.session_state.location_zipcode_input = ""
    if "location_geo_value" not in st.session_state:
        st.session_state.location_geo_value = {}
    if "location_geo_active_request" not in st.session_state:
        st.session_state.location_geo_active_request = ""
    if "location_error_message" not in st.session_state:
        st.session_state.location_error_message = ""
    if "location_inputs_reset_pending" not in st.session_state:
        st.session_state.location_inputs_reset_pending = False

    if st.session_state.get("location_inputs_reset_pending", False):
        st.session_state.location_zipcode_input = ""
        st.session_state.location_error_message = ""
        st.session_state.location_inputs_reset_pending = False


def _render_hidden_geolocation_request(request_key: str, *, trigger_click: bool) -> dict | None:
    geo_col, spacer_col = st.columns([0.02, 0.98], gap="small")
    with geo_col:
        location = streamlit_geolocation()
    with spacer_col:
        st.empty()

    if not trigger_click:
        return location

    components.html(
        textwrap.dedent(
            """
            <script>
            (function () {
              const parentDoc = window.parent && window.parent.document;
              const selfFrame = window.frameElement;
              if (!parentDoc || !selfFrame) {
                return;
              }
              let attempts = 0;
              const triggerClick = function () {
                const frames = Array.from(parentDoc.querySelectorAll("iframe"));
                const selfIndex = frames.indexOf(selfFrame);
                if (selfIndex <= 0) {
                  return;
                }
                const targetFrame = frames[selfIndex - 1];
                if (!targetFrame) {
                  return;
                }
                try {
                  const targetDoc = targetFrame.contentWindow && targetFrame.contentWindow.document;
                  if (!targetDoc) {
                    throw new Error("Missing target document");
                  }
                  const button = targetDoc.querySelector("button");
                  if (button) {
                    button.click();
                    return;
                  }
                } catch (error) {
                  console.debug("NearBite geolocation auto-trigger retry.", error);
                }
                attempts += 1;
                if (attempts < 25) {
                  window.setTimeout(triggerClick, 150);
                }
              };
              triggerClick();
            })();
            </script>
            """
        ).strip(),
        height=0,
        width=0,
    )
    return location


def _process_geolocation_request() -> None:
    _ensure_location_state()

    auto_request = (
        not st.session_state.get("discover_auto_location_requested", False)
        and st.session_state.get("user_lat") is None
        and st.session_state.get("user_lon") is None
    )
    if auto_request:
        st.session_state.location_geo_active_request = "discover_auto"
        st.session_state.location_geo_request_pending = True
        st.session_state.discover_auto_location_requested = True

    active_request = str(st.session_state.get("location_geo_active_request", "") or "")
    if not active_request:
        return

    trigger_click = bool(st.session_state.get("location_geo_request_pending", False))
    location_value = _render_hidden_geolocation_request(
        active_request,
        trigger_click=trigger_click,
    )
    if trigger_click:
        st.session_state.location_geo_request_pending = False

    if not isinstance(location_value, dict):
        return

    latitude = location_value.get("latitude")
    longitude = location_value.get("longitude")
    if latitude is None or longitude is None:
        return

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return

    previous = st.session_state.get("location_geo_value", {}) or {}
    prev_lat = previous.get("latitude")
    prev_lon = previous.get("longitude")
    has_changed = (
        prev_lat != latitude
        or prev_lon != longitude
        or not st.session_state.get("use_my_location", False)
    )

    st.session_state.location_geo_value = {
        "latitude": latitude,
        "longitude": longitude,
    }
    st.session_state.location_geo_active_request = ""
    set_user_origin(latitude, longitude)
    if has_changed:
        st.session_state.discover_page = 1
        st.toast("Using your current location.")
        st.rerun()


def apply_location_draft(restaurants: list[dict[str, Any]]) -> tuple[bool, str | None]:
    _ensure_location_state()
    raw_zipcode = str(st.session_state.get("location_zipcode_input", "")).strip()
    st.session_state.location_error_message = ""

    if not raw_zipcode:
        return True, None

    location = None
    zipcode_location = resolve_zipcode_location(raw_zipcode)
    if zipcode_location:
        location = {
            "label": f"ZIP {raw_zipcode}",
            "lat": float(zipcode_location["lat"]),
            "lon": float(zipcode_location["lon"]),
            "area_label": str(zipcode_location.get("label", "")).strip(),
        }

    if not location:
        message = "We could not match that ZIP code yet. Try a valid NYC ZIP code."
        st.session_state.location_error_message = message
        return False, message

    set_user_origin(float(location["lat"]), float(location["lon"]), zipcode=raw_zipcode)

    st.session_state.location_geo_active_request = ""
    st.session_state.location_geo_request_pending = False
    return True, None


def _reset_location_inputs() -> None:
    st.session_state.location_inputs_reset_pending = True


def reset_location_selection() -> None:
    _ensure_location_state()
    _reset_location_inputs()

    geo_value = st.session_state.get("location_geo_value", {}) or {}
    latitude = geo_value.get("latitude")
    longitude = geo_value.get("longitude")

    if latitude is not None and longitude is not None:
        st.session_state.location_geo_active_request = ""
        st.session_state.location_geo_request_pending = False
        try:
            set_user_origin(float(latitude), float(longitude))
            return
        except (TypeError, ValueError):
            pass

    clear_user_origin()
    st.session_state.location_geo_active_request = "discover_manual"
    st.session_state.location_geo_request_pending = True


def _render_origin_summary() -> None:
    origin = get_current_origin()
    area_html = (
        f"<div class='nb-location-inline-area'>Area: {html.escape(origin['area_label'])}</div>"
        if origin.get("area_label")
        else ""
    )
    st.markdown(
        textwrap.dedent(
            f"""
            <div class="nb-location-inline">
              <div class="nb-location-inline-label">Current origin</div>
              <div class="nb-location-inline-value"><strong>{html.escape(origin['label'])}</strong></div>
              {area_html}
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_location_summary() -> None:
    _process_geolocation_request()
    _render_origin_summary()


def render_location_controls(restaurants: list[dict[str, Any]]) -> None:
    _ensure_location_state()

    zipcode_options = [""] + get_supported_zipcode_options()
    current_zipcode = str(st.session_state.get("location_zipcode_input", "") or "")
    if current_zipcode not in zipcode_options:
        st.session_state.location_zipcode_input = ""

    st.selectbox(
        "ZIP code",
        options=zipcode_options,
        key="location_zipcode_input",
        format_func=lambda value: (
            "Select a ZIP code"
            if not value
            else f"{value} · {resolve_zipcode_location(value).get('label', '')}"
        ),
    )

    error_message = str(st.session_state.get("location_error_message", "") or "").strip()
    if error_message:
        st.warning(error_message)

    if st.button("Current location", key="location_current_button", use_container_width=True):
        _reset_location_inputs()
        st.session_state.location_geo_active_request = "discover_manual"
        st.session_state.location_geo_request_pending = True
        st.session_state.discover_page = 1
        st.rerun()
