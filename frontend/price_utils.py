"""
frontend/price_utils.py
Owner: Jonas Chen

Responsibilities:
- Normalizes price labels for frontend questionnaire and display use
- Keeps price display helpers out of backend integration modules
- Provides a lightweight UI-owned price vocabulary layer
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
