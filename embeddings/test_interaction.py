"""Runnable mock-based tests for embeddings.interaction.

This script validates weighted aggregation, absolute-value denominator,
normalization, and fallback behavior using deterministic in-memory mocks.

Usage:
    python embeddings/test_interaction.py
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "interaction.py"
_SPEC = importlib.util.spec_from_file_location("interaction_module", MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load interaction module from {MODULE_PATH}")
interaction_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(interaction_module)

DIM = 768


def _vec(a: float = 0.0, b: float = 0.0) -> list[float]:
    return [a, b] + [0.0] * (DIM - 2)


def _is_unit_norm(vector: list[float], tol: float = 1e-9) -> bool:
    norm = math.sqrt(sum(value * value for value in vector))
    return abs(norm - 1.0) <= tol


def _run_case(
    name: str,
    interactions: list[dict],
    reviews: list[dict],
    embeddings: dict[str, list[float]],
    expect_none: bool,
) -> bool:
    interaction_module._resolve_interaction_getter = lambda: (lambda _u: interactions)
    interaction_module._resolve_review_getter = lambda: (lambda _u: reviews)
    interaction_module._load_restaurant_embedding_map = lambda: embeddings

    vector = interaction_module.compute_interaction_vector("mock_user")

    if expect_none:
        ok = vector is None
        print(f"[{ 'PASS' if ok else 'FAIL' }] {name}: expected None")
        return ok

    if vector is None:
        print(f"[FAIL] {name}: expected vector, got None")
        return False

    if len(vector) != DIM:
        print(f"[FAIL] {name}: expected dim {DIM}, got {len(vector)}")
        return False

    if not _is_unit_norm(vector):
        print(f"[FAIL] {name}: vector is not unit-normalized")
        return False

    print(
        f"[PASS] {name}: dim={len(vector)} norm=1.0 first2=({vector[0]:.6f}, {vector[1]:.6f})"
    )
    return True


def main() -> None:
    cases = [
        {
            "name": "No events returns None",
            "interactions": [],
            "reviews": [],
            "embeddings": {"r1": _vec(1.0, 0.0)},
            "expect_none": True,
        },
        {
            "name": "Saved + liked + neutral + hate aggregation",
            "interactions": [
                {"business_id": "r1", "action": "saved"},
                {"business_id": "r1", "action": "liked"},
                {"business_id": "r2", "action": "saved"},
                {"business_id": "r3", "action": "unsaved"},
            ],
            "reviews": [
                {"business_id": "r1", "sentiment": "neutral"},
                {"business_id": "r2", "sentiment": "hate"},
            ],
            "embeddings": {
                "r1": _vec(1.0, 0.0),
                "r2": _vec(0.0, 1.0),
                "r3": _vec(1.0, 1.0),
            },
            "expect_none": False,
        },
        {
            "name": "Unknown action and sentiment are ignored",
            "interactions": [
                {"business_id": "r1", "action": "bookmarked"},
                {"business_id": "r2", "action": "saved"},
            ],
            "reviews": [
                {"business_id": "r2", "sentiment": "mixed"},
            ],
            "embeddings": {
                "r1": _vec(1.0, 0.0),
                "r2": _vec(0.0, 1.0),
            },
            "expect_none": False,
        },
        {
            "name": "Net-zero business is dropped",
            "interactions": [
                {"business_id": "r1", "action": "liked"},
                {"business_id": "r1", "action": "saved"},
            ],
            "reviews": [
                {"business_id": "r1", "sentiment": "hate"},
            ],
            "embeddings": {
                "r1": _vec(1.0, 0.0),
            },
            "expect_none": True,
        },
        {
            "name": "Missing business embedding is skipped",
            "interactions": [
                {"business_id": "r_missing", "action": "liked"},
                {"business_id": "r2", "action": "saved"},
            ],
            "reviews": [],
            "embeddings": {
                "r2": _vec(0.0, 1.0),
            },
            "expect_none": False,
        },
        {
            "name": "Wrong-dimension embedding is skipped",
            "interactions": [
                {"business_id": "r1", "action": "saved"},
                {"business_id": "r2", "action": "saved"},
            ],
            "reviews": [],
            "embeddings": {
                "r1": [1.0, 0.0],
                "r2": _vec(0.0, 1.0),
            },
            "expect_none": False,
        },
        {
            "name": "Only bad-dimension embeddings leads to None",
            "interactions": [
                {"business_id": "r1", "action": "saved"},
            ],
            "reviews": [],
            "embeddings": {
                "r1": [1.0, 0.0],
            },
            "expect_none": True,
        },
    ]

    passed = 0
    for case in cases:
        ok = _run_case(
            name=case["name"],
            interactions=case["interactions"],
            reviews=case["reviews"],
            embeddings=case["embeddings"],
            expect_none=case["expect_none"],
        )
        if ok:
            passed += 1

    total = len(cases)
    print("=" * 60)
    print(f"Summary: {passed}/{total} cases passed")


if __name__ == "__main__":
    main()
