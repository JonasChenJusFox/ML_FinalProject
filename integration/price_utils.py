"""
integration/price_utils.py

Shared helpers for normalizing price labels across questionnaire, search,
ranking, and display code.
"""

from __future__ import annotations

from typing import Any

PRICE_LABELS = ["cheap", "moderate", "expensive", "luxury"]

_PRICE_ALIAS_TO_LABEL = {
    "$": "cheap",
    "$$": "moderate",
    "$$$": "expensive",
    "$$$$": "luxury",
    "1": "cheap",
    "2": "moderate",
    "3": "expensive",
    "4": "luxury",
    "cheap": "cheap",
    "budget": "cheap",
    "affordable": "cheap",
    "inexpensive": "cheap",
    "moderate": "moderate",
    "mid range": "moderate",
    "mid-range": "moderate",
    "reasonably priced": "moderate",
    "expensive": "expensive",
    "pricey": "expensive",
    "upscale": "expensive",
    "luxury": "luxury",
    "fine dining": "luxury",
    "premium": "luxury",
    "high end": "luxury",
    "high-end": "luxury",
}

_PRICE_LEVELS = {
    "cheap": 1.0,
    "moderate": 2.0,
    "expensive": 3.0,
    "luxury": 4.0,
}


def canonicalize_price_label(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        rounded = int(round(float(value)))
        return _PRICE_ALIAS_TO_LABEL.get(str(rounded), "")

    text = str(value).strip().lower()
    if not text:
        return ""

    return _PRICE_ALIAS_TO_LABEL.get(text, "")


def price_level_value(value: Any) -> float:
    canonical = canonicalize_price_label(value)
    if canonical:
        return _PRICE_LEVELS.get(canonical, 0.0)

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def price_label_from_level(value: Any) -> str:
    numeric = int(round(price_level_value(value)))
    return _PRICE_ALIAS_TO_LABEL.get(str(numeric), "")
