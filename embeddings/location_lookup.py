"""Location coordinate lookup for query and UI-based location parsing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def _load_neighborhood_centroids() -> dict:
    """Load neighborhood centroids from JSON."""
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "data" / "nyc_neighborhood_centroids.json"
    
    if not path.exists():
        return {}
    
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    
    return {}


def _load_zipcode_centroids() -> dict:
    """Load zipcode centroids from JSON."""
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "data" / "nyc_zipcode_centroids.json"
    
    if not path.exists():
        return {}
    
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    
    return {}


def _load_location_keyword_map() -> dict:
    """Load location keyword map (NYU -> neighborhood mapping)."""
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "data" / "nyc_location_keyword_map.json"
    
    if not path.exists():
        return {}
    
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    
    return {}


# Lazy-loaded caches
NEIGHBORHOOD_CENTROIDS: dict = _load_neighborhood_centroids()
ZIPCODE_CENTROIDS: dict = _load_zipcode_centroids()
LOCATION_KEYWORD_MAP: dict = _load_location_keyword_map()


def lookup_neighborhood_coordinate(neighborhood: str) -> Optional[tuple[float, float]]:
    """Look up centroid [lat, lon] for a neighborhood.
    
    Args:
        neighborhood: Neighborhood name (case-insensitive)
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    if not neighborhood:
        return None
    
    # Exact match first
    if neighborhood in NEIGHBORHOOD_CENTROIDS:
        coord = NEIGHBORHOOD_CENTROIDS[neighborhood]
        if isinstance(coord, list) and len(coord) == 2:
            return tuple(coord)
    
    # Case-insensitive match
    normalized = neighborhood.lower().strip()
    for key, coord in NEIGHBORHOOD_CENTROIDS.items():
        if key.lower() == normalized and isinstance(coord, list) and len(coord) == 2:
            return tuple(coord)
    
    return None


def lookup_zipcode_coordinate(zipcode: str) -> Optional[tuple[float, float]]:
    """Look up centroid [lat, lon] for a zipcode.
    
    Args:
        zipcode: Zipcode string
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    if not zipcode:
        return None
    
    # Exact match
    if zipcode in ZIPCODE_CENTROIDS:
        coord = ZIPCODE_CENTROIDS[zipcode]
        if isinstance(coord, list) and len(coord) == 2:
            return tuple(coord)
    
    return None


def resolve_location_coordinate(location: str) -> Optional[tuple[float, float]]:
    """Resolve a location string (neighborhood, zipcode, or keyword) to coordinates.
    
    Args:
        location: Location string (could be neighborhood name, zipcode, or keyword)
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    if not location:
        return None
    
    location_str = str(location).strip()
    
    # Check if it's a zipcode
    if location_str.isdigit() and len(location_str) == 5:
        return lookup_zipcode_coordinate(location_str)
    
    # Try direct neighborhood lookup
    result = lookup_neighborhood_coordinate(location_str)
    if result:
        return result
    
    # Check if it's a keyword that maps to a neighborhood
    if location_str in LOCATION_KEYWORD_MAP:
        neighborhood = LOCATION_KEYWORD_MAP[location_str]
        return lookup_neighborhood_coordinate(neighborhood)
    
    # Case-insensitive keyword lookup
    normalized = location_str.lower().strip()
    for keyword, neighborhood in LOCATION_KEYWORD_MAP.items():
        if keyword.lower() == normalized:
            return lookup_neighborhood_coordinate(neighborhood)
    
    return None
