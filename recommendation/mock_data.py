"""Small mock dataset for local testing of the ranking module."""

from __future__ import annotations

MOCK_RESTAURANTS: list[dict] = [
    {
        "business_id": "nearbite-001",
        "name": "Alice's Garden Table",
        "embedding": [0.92, 0.10, 0.13, 0.30, 0.20],
        "cluster_id": 0,
        "rating": 4.7,
        "review_count": 1240,
        "price": "$$",
        "distance_km": 1.2,
        "categories": ["American", "Brunch", "Salads"],
    },
    {
        "business_id": "nearbite-002",
        "name": "Bodega Bowl",
        "embedding": [0.78, 0.18, 0.10, 0.34, 0.23],
        "cluster_id": 0,
        "rating": 4.4,
        "review_count": 860,
        "price": "$",
        "distance_km": 0.8,
        "categories": ["Healthy", "Bowls", "Lunch"],
    },
    {
        "business_id": "nearbite-003",
        "name": "Saffron Street Kitchen",
        "embedding": [0.40, 0.74, 0.08, 0.44, 0.20],
        "cluster_id": 1,
        "rating": 4.8,
        "review_count": 2140,
        "price": "$$$",
        "distance_km": 3.4,
        "categories": ["Indian", "Dinner", "Spicy"],
    },
    {
        "business_id": "nearbite-004",
        "name": "Metro Pizza Loft",
        "embedding": [0.12, 0.12, 0.90, 0.20, 0.12],
        "cluster_id": 2,
        "rating": 4.1,
        "review_count": 540,
        "price": "$$",
        "distance_km": 2.5,
        "categories": ["Pizza", "Casual", "Late Night"],
    },
    {
        "business_id": "nearbite-005",
        "name": "Harbor Noodle Bar",
        "embedding": [0.36, 0.69, 0.10, 0.52, 0.24],
        "cluster_id": 1,
        "rating": 4.6,
        "review_count": 1675,
        "price": "$$",
        "distance_km": 4.0,
        "categories": ["Asian", "Noodles", "Takeout"],
    },
    {
        "business_id": "nearbite-006",
        "name": "Firebrick Slice Co.",
        "embedding": [0.18, 0.14, 0.86, 0.24, 0.14],
        "cluster_id": 2,
        "rating": 4.3,
        "review_count": 980,
        "price": "$$",
        "distance_km": 1.7,
        "categories": ["Pizza", "Italian", "Dinner"],
    },
    {
        "business_id": "nearbite-007",
        "name": "Green Market Cafe",
        "embedding": [0.84, 0.16, 0.12, 0.28, 0.24],
        "cluster_id": 0,
        "rating": 4.5,
        "review_count": 720,
        "price": "$$",
        "distance_km": 2.1,
        "categories": ["Cafe", "Healthy", "Vegetarian"],
    },
]

SAMPLE_QUERY_VEC: list[float] = [0.88, 0.12, 0.14, 0.28, 0.20]
SAMPLE_USER_VEC: list[float] = [0.80, 0.18, 0.12, 0.35, 0.25]

SAMPLE_CLUSTER_CENTROIDS: dict[int, list[float]] = {
    0: [0.85, 0.16, 0.12, 0.31, 0.22],
    1: [0.38, 0.72, 0.09, 0.48, 0.22],
    2: [0.15, 0.14, 0.88, 0.22, 0.13],
}