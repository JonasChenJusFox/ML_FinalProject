"""
frontend/adapters.py
Owner: Jonas Chen

Responsibilities:
- Converts raw restaurant records into frontend-friendly display data
- Normalizes fields such as address, price, image, and review snippet
- Computes travel time from the current origin
- Provides helper functions for wrapped statistics and frontend filters
- Keeps UI rendering logic separate from raw dataset structure
"""

from __future__ import annotations

import re
from collections import Counter

import streamlit as st

from integration.api import (
    NYU_LAT,
    NYU_LON,
    manhattan_distance_km as _manhattan_distance_km,
    walking_minutes_from_distance_km as _walking_minutes_from_distance_km,
)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def shorten_text(value: str, limit: int = 160) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_current_origin() -> dict:
    if (
        st.session_state.get("use_my_location", False)
        and st.session_state.get("user_lat") is not None
        and st.session_state.get("user_lon") is not None
    ):
        return {
            "label": "My location",
            "lat": float(st.session_state["user_lat"]),
            "lon": float(st.session_state["user_lon"]),
        }

    return {
        "label": "NYU",
        "lat": NYU_LAT,
        "lon": NYU_LON,
    }


def set_user_origin(lat: float, lon: float) -> None:
    st.session_state.use_my_location = True
    st.session_state.user_lat = float(lat)
    st.session_state.user_lon = float(lon)


def reset_origin_to_nyu() -> None:
    st.session_state.use_my_location = False
    st.session_state.user_lat = None
    st.session_state.user_lon = None



def _minutes_from_current_origin(lat: float, lon: float) -> int:
    if not lat or not lon:
        return 0

    origin = get_current_origin()
    km = _manhattan_distance_km(origin["lat"], origin["lon"], lat, lon)
    minutes = _walking_minutes_from_distance_km(km)
    return int(minutes or 0)


def _extract_review_snippet(reviews: list) -> str:
    for item in reviews:
        if isinstance(item, dict):
            text = clean_text(item.get("text", ""))
            if text:
                return text
        elif isinstance(item, str):
            text = clean_text(item)
            if text:
                return text
    return ""


def _extract_image_url(raw: dict) -> str:
    image_url = clean_text(raw.get("image_url", ""))
    if image_url:
        return image_url

    images = raw.get("images", [])
    if isinstance(images, list) and images:
        return clean_text(images[0])

    return ""


def _extract_address(raw: dict) -> str:
    direct = clean_text(raw.get("address", ""))
    if direct:
        return direct

    # First choice: address1/2/3
    parts = [
        clean_text(raw.get("address1", "")),
        clean_text(raw.get("address2", "")),
        clean_text(raw.get("address3", "")),
    ]
    parts = [part for part in parts if part]
    if parts:
        return ", ".join(parts)

    # Second choice: display_address, but clean it up
    display_address = raw.get("display_address", [])
    if isinstance(display_address, list):
        cleaned = [clean_text(x) for x in display_address if clean_text(x)]

        name = clean_text(raw.get("name", ""))
        if cleaned and name and cleaned[0].lower() == name.lower():
            cleaned = cleaned[1:]

        cleaned = [
            item for item in cleaned
            if "community board" not in item.lower()
            and "county" not in item.lower()
            and item.lower() != "united states"
        ]

        if cleaned:
            return ", ".join(cleaned[:3])

    return "Address not listed"


def _extract_price_display(raw: dict) -> str:
    price = clean_text(raw.get("price", ""))
    if price:
        return price

    price_original = clean_text(raw.get("price_original", ""))
    if price_original:
        return price_original

    try:
        price_level = int(raw.get("price_level", 0) or 0)
    except (TypeError, ValueError):
        price_level = 0

    if price_level > 0:
        return "$" * price_level

    return "Price not listed"


def normalize_restaurant(raw: dict) -> dict:
    categories = raw.get("categories", [])
    if not isinstance(categories, list):
        categories = [str(categories)] if categories else []
    categories = [clean_text(x) for x in categories if clean_text(x)]

    reviews = raw.get("google_reviews", [])
    if not isinstance(reviews, list):
        reviews = []

    coords = raw.get("coordinates") or {}
    lat = _safe_float(raw.get("latitude") or coords.get("latitude"), 0.0)
    lon = _safe_float(raw.get("longitude") or coords.get("longitude"), 0.0)

    backend_distance_km = raw.get("distance_km")
    normalized_distance_km = (
        _safe_float(backend_distance_km, 0.0)
        if backend_distance_km is not None
        else None
    )

    backend_travel_minutes = raw.get("travel_minutes")
    if backend_travel_minutes is not None:
        travel_minutes = int(_safe_float(backend_travel_minutes, 0.0))
    elif normalized_distance_km is not None:
        travel_minutes = int(_walking_minutes_from_distance_km(normalized_distance_km) or 0)
    else:
        travel_minutes = _minutes_from_current_origin(lat, lon)

    return {
    "business_id": clean_text(raw.get("business_id", "")),
    "name": clean_text(raw.get("name", "Unknown")),
    "categories": categories,
    "borough": clean_text(raw.get("borough", "Unknown")),
    "rating": _safe_float(raw.get("rating"), 0.0),

    "price_display": _extract_price_display(raw),
    "price": clean_text(raw.get("price", "")),
    "price_original": clean_text(raw.get("price_original", "")),
    "price_level": raw.get("price_level", 0),

    "address": _extract_address(raw),
    "latitude": lat,
    "longitude": lon,
    "image_url": _extract_image_url(raw),
    "review_snippet": _extract_review_snippet(reviews),
    "google_reviews": reviews,
    "url": clean_text(raw.get("url", "")),
    "score": _safe_float(raw.get("score", 0.0)),
    "distance_km": normalized_distance_km,
    "travel_minutes": travel_minutes,
}


def normalize_results(restaurants: list[dict]) -> list[dict]:
    return [normalize_restaurant(item) for item in restaurants if isinstance(item, dict)]


def sort_results(restaurants: list[dict], focus_business_id: str | None = None) -> list[dict]:
    normalized = normalize_results(restaurants)

    if not focus_business_id:
        return normalized

    focused = [item for item in normalized if item["business_id"] == focus_business_id]
    remainder = [item for item in normalized if item["business_id"] != focus_business_id]
    return focused + remainder


def get_filter_options(restaurants: list[dict]) -> dict:
    normalized = normalize_results(restaurants)

    categories = sorted(
        {
            category
            for item in normalized
            for category in item.get("categories", [])
            if category
        }
    )
    boroughs = sorted(
        {
            item.get("borough", "")
            for item in normalized
            if item.get("borough", "")
        }
    )
    prices = sorted(
        {
            item.get("price_display", "")
            for item in normalized
            if item.get("price_display", "")
            and item.get("price_display", "") != "Price not listed"
        },
        key=lambda value: (len(value), value),
    )

    return {
        "categories": categories,
        "boroughs": boroughs,
        "prices": prices,
    }


def get_wrapped_summary(restaurants: list[dict], saved_ids: list[str], viewed_ids: list[str]) -> dict:
    normalized = normalize_results(restaurants)
    used_ids = list(dict.fromkeys(viewed_ids + saved_ids))
    chosen = [item for item in normalized if item["business_id"] in used_ids]

    if not chosen:
        return {
            "top_cuisine": "No data yet",
            "top_borough": "No data yet",
            "avg_price": "—",
            "new_cuisines": 0,
        }

    cuisine_counter = Counter()
    borough_counter = Counter()
    price_values = []

    for item in chosen:
        if item["categories"]:
            cuisine_counter[item["categories"][0]] += 1
        if item["borough"]:
            borough_counter[item["borough"]] += 1

        price_text = item["price_display"]
        if price_text not in {"—", "Price not listed"}:
            price_values.append(price_text.count("$"))

    avg_price_num = round(sum(price_values) / len(price_values)) if price_values else 0
    avg_price = "$" * avg_price_num if avg_price_num > 0 else "—"

    all_cuisines = {cuisine for item in chosen for cuisine in item["categories"]}

    return {
        "top_cuisine": cuisine_counter.most_common(1)[0][0] if cuisine_counter else "No data yet",
        "top_borough": borough_counter.most_common(1)[0][0] if borough_counter else "No data yet",
        "avg_price": avg_price,
        "new_cuisines": len(all_cuisines),
    }
