"""Lightweight utilities used by the recommendation ranking module."""

from __future__ import annotations

import math
from typing import Any


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Clamp a value to the inclusive range ``[lower, upper]``."""
    return max(lower, min(upper, value))


def to_float(value: Any, default: float = 0.0) -> float:
    """Convert ``value`` to ``float`` with a safe fallback."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_value(value: float | None, minimum: float, maximum: float) -> float:
    """Normalize ``value`` into the range ``[0, 1]``."""
    if value is None:
        return 0.0
    if maximum <= minimum:
        return 0.0
    return clamp((value - minimum) / (maximum - minimum))


def normalized_text(value: str | None) -> str:
    """Normalize text for case-insensitive matching."""
    if not value:
        return ""
    return value.strip().lower()


def price_level_value(price_level: Any) -> float:
    """Convert common price formats such as ``$$`` or ``3`` into a level."""
    if price_level is None:
        return 0.0

    if isinstance(price_level, str):
        stripped = price_level.strip()
        if not stripped:
            return 0.0
        if "$" in stripped:
            return float(stripped.count("$"))
        return to_float(stripped, 0.0)

    return to_float(price_level, 0.0)


def price_level_from_numeric(value: float | None) -> str:
    """Return a compact price label from a numeric price level."""
    numeric_value = int(round(to_float(value, 0.0)))
    if numeric_value <= 0:
        return ""
    return "$" * numeric_value


def distance_score(distance_km: float | None, max_distance_km: float = 10.0) -> float:
    """Return a proximity score where closer restaurants score higher."""
    if distance_km is None:
        return 0.5
    if max_distance_km <= 0:
        return 0.5
    distance_value = max(0.0, to_float(distance_km, 0.0))
    score = 1.0 - (distance_value / max_distance_km)
    return clamp(score)


def safe_log1p(value: float | None) -> float:
    """Compute ``log(1 + value)`` safely for non-negative inputs."""
    numeric_value = max(0.0, to_float(value, 0.0))
    return math.log1p(numeric_value)
