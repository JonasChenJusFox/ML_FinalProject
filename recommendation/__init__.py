"""Public exports for the recommendation package."""

from __future__ import annotations

from typing import Any

__all__ = [
	"cosine_similarity",
	"fuse_vectors",
	"rank_candidates",
]


def __getattr__(name: str) -> Any:
	"""Lazily re-export ranking helpers from :mod:`recommendation.ranker`."""
	if name in __all__:
		from recommendation import ranker

		return getattr(ranker, name)
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
	"""Return package attributes including the public exports."""
	return sorted(list(globals().keys()) + __all__)
