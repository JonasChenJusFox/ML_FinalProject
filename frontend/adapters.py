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

from frontend.location_utils import (
    find_nearest_search_area,
    get_location_filter_options,
    haversine_km as _haversine_km,
    infer_borough,
)

WALKING_KM_PER_MINUTE = 5.0 / 60.0


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def display_text(value: str) -> str:
    return clean_text(str(value or "").replace("_", " "))


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
        latitude = float(st.session_state["user_lat"])
        longitude = float(st.session_state["user_lon"])
        coords_key = (round(latitude, 5), round(longitude, 5))
        if st.session_state.get("origin_label_cache_key") != coords_key:
            nearest_area = find_nearest_search_area(latitude, longitude)
            nearest_street = _find_nearest_street_label(latitude, longitude)
            selected_zipcode = clean_text(st.session_state.get("selected_zipcode", ""))
            if selected_zipcode:
                label = f"ZIP {selected_zipcode}"
                travel_label = nearest_area["name"] if nearest_area else f"ZIP {selected_zipcode}"
                area_label = nearest_area["name"] if nearest_area else ""
            else:
                label = nearest_street or (nearest_area["name"] if nearest_area else f"{latitude:.4f}, {longitude:.4f}")
                travel_label = nearest_street or (nearest_area["name"] if nearest_area else "Current location")
                area_label = nearest_area["name"] if nearest_area else ""
            st.session_state.origin_label_cache_key = coords_key
            st.session_state.origin_label = label
            st.session_state.origin_travel_label = travel_label
            st.session_state.origin_area_label = area_label

        return {
            "label": st.session_state.get("origin_label", "Current location"),
            "travel_label": st.session_state.get("origin_travel_label", "Current location"),
            "area_label": st.session_state.get("origin_area_label", ""),
            "lat": latitude,
            "lon": longitude,
        }

    return {
        "label": "Location not set",
        "travel_label": "",
        "area_label": "",
        "lat": None,
        "lon": None,
    }


def get_current_origin_kwargs() -> dict:
    origin = get_current_origin()
    return {
        "origin_lat": origin["lat"],
        "origin_lon": origin["lon"],
    }


def set_user_origin(lat: float, lon: float, *, zipcode: str | None = None) -> None:
    st.session_state.use_my_location = True
    st.session_state.user_lat = float(lat)
    st.session_state.user_lon = float(lon)
    st.session_state.selected_zipcode = clean_text(zipcode) if zipcode else ""
    st.session_state.origin_label_cache_key = None


def clear_user_origin() -> None:
    st.session_state.use_my_location = False
    st.session_state.user_lat = None
    st.session_state.user_lon = None
    st.session_state.selected_zipcode = ""
    st.session_state.origin_label = ""
    st.session_state.origin_travel_label = ""
    st.session_state.origin_area_label = ""
    st.session_state.origin_label_cache_key = None



def _extract_coordinates(raw: dict) -> tuple[float, float]:
    coordinates = raw.get("coordinates", {})

    lat = _safe_float(raw.get("latitude"), 0.0)
    lon = _safe_float(raw.get("longitude"), 0.0)

    if isinstance(coordinates, dict):
        if not lat:
            lat = _safe_float(coordinates.get("latitude"), 0.0)
        if not lon:
            lon = _safe_float(coordinates.get("longitude"), 0.0)

    return lat, lon


def _minutes_from_current_origin(lat: float, lon: float) -> int:
    if not lat or not lon:
        return 0

    origin = get_current_origin()
    if origin["lat"] is None or origin["lon"] is None:
        return 0
    km = _haversine_km(origin["lat"], origin["lon"], lat, lon)

    # Use a conservative walking-speed estimate so the card UI does not
    # understate travel time by a large margin.
    return max(3, round(km / WALKING_KM_PER_MINUTE))


def _street_segment(address: str) -> str:
    street = clean_text(address).split(",")[0].strip()
    return street


def _find_nearest_street_label(latitude: float, longitude: float) -> str:
    candidates = st.session_state.get("preview_restaurants", []) or []
    nearest_street = ""
    nearest_distance = None

    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        lat, lon = _extract_coordinates(raw)
        if not lat or not lon:
            continue
        address = _extract_address(raw)
        street = _street_segment(address)
        if not street or street == "Address not listed":
            continue

        distance = _haversine_km(latitude, longitude, lat, lon)
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_street = street

    if not nearest_street:
        return ""

    if nearest_distance is not None and nearest_distance <= 0.25:
        return nearest_street

    return f"Near {nearest_street}"


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


def _extract_description(raw: dict) -> str:
    description = clean_text(raw.get("embedding_text", ""))
    if description:
        return description
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


def _extract_location_search_text(raw: dict) -> str:
    display_address = raw.get("display_address", [])
    display_text = " ".join(
        clean_text(item) for item in display_address
        if clean_text(item)
    ) if isinstance(display_address, list) else clean_text(display_address)

    parts = [
        raw.get("address", ""),
        raw.get("address1", ""),
        raw.get("address2", ""),
        raw.get("address3", ""),
        raw.get("city", ""),
        raw.get("neighborhood", ""),
        raw.get("borough", ""),
        display_text,
    ]
    return clean_text(" ".join(clean_text(part) for part in parts if clean_text(part)))


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

    lat, lon = _extract_coordinates(raw)

    return {
        "business_id": clean_text(raw.get("business_id", "")),
        "name": clean_text(raw.get("name", "Unknown")),
        "categories": categories,
        "borough": display_text(infer_borough(raw) or "Unknown"),
        "rating": _safe_float(raw.get("rating"), 0.0),
        "price_display": _extract_price_display(raw),
        "price": clean_text(raw.get("price", "")),
        "price_original": clean_text(raw.get("price_original", "")),
        "price_level": raw.get("price_level", 0),
        "address": _extract_address(raw),
        "location_search_text": _extract_location_search_text(raw),
        "latitude": lat,
        "longitude": lon,
        "image_url": _extract_image_url(raw),
        "review_snippet": _extract_review_snippet(reviews),
        "description": _extract_description(raw),
        "google_reviews": reviews,
        "url": clean_text(raw.get("url", "")),
        "score": _safe_float(raw.get("score", raw.get("final_score", 0.0)), 0.0),
        "travel_minutes": _minutes_from_current_origin(lat, lon),
    }


def normalize_results(restaurants: list[dict]) -> list[dict]:
    return [normalize_restaurant(item) for item in restaurants if isinstance(item, dict)]


def sort_results(restaurants: list[dict], focus_business_id: str | None = None) -> list[dict]:
    normalized = normalize_results(restaurants)

    def sort_key(item: dict):
        focused_rank = 0 if focus_business_id and item["business_id"] == focus_business_id else 1
        return (
            focused_rank,
            -(item.get("score", 0.0) or 0.0),
            -(item.get("rating", 0.0) or 0.0),
            item.get("name", ""),
        )

    return sorted(normalized, key=sort_key)


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
            *get_location_filter_options(),
            *{
                item.get("borough", "")
                for item in normalized
                if item.get("borough", "")
            },
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
