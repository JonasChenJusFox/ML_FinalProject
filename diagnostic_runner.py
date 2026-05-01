#!/usr/bin/env python3
"""Run fixed test queries for ``test_user_11`` and dump detailed scores (no app UI changes)."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from embeddings.query_parser import parse_query, minimal_clean_query
from embeddings.vectorizer import embed_query
from embeddings.cluster_retrieval import load_restaurant_index, load_centroids, retrieve_candidates
from recommendation.ranker import rank_candidates, _restaurant_search_text
from integration.api import (
    search_restaurants,
    _with_distance_km,
    _build_user_embedding_if_available,
    _build_interaction_vector,
    _blend_vectors,
    _build_filter_stages,
    _adapt_filters,
    _merge_query_signals,
    _retrieve_candidates_cluster_first,
    apply_strict_filters,
    _safe_float,
)
from integration.user_repo import get_user_profile, find_user_by_username, create_user, save_user_profile
from data.pipeline import load_restaurants

# Test queries
TEST_QUERIES = [
    "italian pasta in West Village",
    "mexican tacos in Lower East Side",
    "sushi near SoHo",
    "burgers near 10012",
    "lunch in Midtown",
    "something good for dinner",
    "cheap vegan brunch near Tribeca",
    "highly rated dessert place in Times Square",
    "cheap steakhouse near East Village",
    "quick coffee under $5",
]

TEST_USER_ID = "test_user_11"


def extract_diagnostic_info(
    query: str,
    results: list[dict],
    parsed_query: dict | None = None,
) -> dict:
    """Extract and structure diagnostic information for a query."""
    diagnostic = {
        "query": query,
        "parsed_query": parsed_query,
        "top_3_results": [],
    }

    for idx, result in enumerate(results[:3]):
        result_info = {
            "rank": idx + 1,
            "restaurant_name": result.get("name", "Unknown"),
            "categories": result.get("categories", []),
            "address": result.get("address", ""),
            "borough": result.get("borough", ""),
            "neighborhood": result.get("neighborhood", ""),
            "distance_km": result.get("distance_km"),
            "travel_minutes": result.get("travel_minutes"),
            "final_score": result.get("final_score"),
            "semantic_score": result.get("semantic_score"),
            "score_breakdown": result.get("score_breakdown", {}),
            "soft_preference_boost": result.get("soft_preference_boost"),
            "dietary_match_boost": result.get("dietary_match_boost"),
        }

        # Identify what contributed most to the score
        breakdown = result.get("score_breakdown", {})
        if breakdown:
            weighted_components = {}
            for key, value in breakdown.items():
                if key not in ("dietary_match", "location_match", "cuisine_match", "price_filter_match", "vibe_match", "meal_type_match", "total_filter_boost"):
                    # These are main scoring components
                    weighted_components[key] = value

            if weighted_components:
                max_contributor = max(weighted_components.items(), key=lambda x: x[1])
                result_info["max_score_contributor"] = {
                    "component": max_contributor[0],
                    "value": max_contributor[1],
                }

        diagnostic["top_3_results"].append(result_info)

    return diagnostic


def analyze_query_intent(parsed_query: dict | None) -> dict:
    """Analyze parsed query intent."""
    if not parsed_query:
        return {"intent": "no_parsing"}

    analysis = {
        "cuisines": parsed_query.get("cuisines", []),
        "location": parsed_query.get("location"),
        "price": parsed_query.get("price"),
        "dietary": parsed_query.get("dietary", []),
        "meal_context": parsed_query.get("meal_context"),
        "occasion": parsed_query.get("occasion"),
        "cleaned_query": parsed_query.get("cleaned_query"),
    }

    return analysis


def diagnose_result(
    query: str,
    parsed_query: dict | None,
    results: list[dict],
    all_restaurants: list[dict],
) -> dict:
    """Diagnose potential issues with a query result."""
    diagnosis = {
        "query": query,
        "diagnostics": [],
    }

    if not results:
        diagnosis["diagnostics"].append({
            "type": "retrieval_problem",
            "severity": "critical",
            "message": "No results returned from search",
        })
        return diagnosis

    top_result = results[0]
    top_semantic_score = top_result.get("semantic_score", 0.0)
    top_final_score = top_result.get("final_score", 0.0)

    # Check semantic score as confidence signal
    if top_semantic_score < 0.3:
        diagnosis["diagnostics"].append({
            "type": "retrieval_problem",
            "severity": "high",
            "message": f"Low semantic_score ({top_semantic_score:.3f}) - query may not match intent",
        })

    # Check score diversity
    if len(results) >= 3:
        scores = [r.get("final_score", 0.0) for r in results[:3]]
        gap_1_2 = scores[0] - scores[1]
        gap_1_3 = scores[0] - scores[2]
        if gap_1_2 < 0.01 and gap_1_3 < 0.02:
            diagnosis["diagnostics"].append({
                "type": "ranker_weighting_problem",
                "severity": "medium",
                "message": f"Small score gap between top results - ranking may be unstable",
                "gaps": {"top1_top2": gap_1_2, "top1_top3": gap_1_3},
            })

    # Check cuisine matching
    if parsed_query and parsed_query.get("cuisines"):
        expected_cuisines = [str(c).lower() for c in parsed_query.get("cuisines", [])]
        top_categories = top_result.get("categories", [])
        top_categories_lower = [str(c).lower() if isinstance(c, str) else (c.get("title", "").lower() if isinstance(c, dict) else "") for c in top_categories]

        cuisine_match = any(ec in " ".join(top_categories_lower) for ec in expected_cuisines)
        if not cuisine_match:
            diagnosis["diagnostics"].append({
                "type": "parser_problem",
                "severity": "medium",
                "message": f"Top result doesn't match parsed cuisine intent: {expected_cuisines}",
                "parsed_cuisines": expected_cuisines,
                "result_categories": top_categories,
            })

    # Check location matching
    if parsed_query and parsed_query.get("location"):
        location = parsed_query.get("location")
        location_label = None
        if isinstance(location, dict):
            location_label = location.get("label")
        elif isinstance(location, str):
            location_label = location

        if location_label:
            result_neighborhood = top_result.get("neighborhood", "").lower()
            result_borough = top_result.get("borough", "").lower()
            location_lower = str(location_label).lower()

            location_match = (location_lower in result_neighborhood or location_lower in result_borough or
                            result_neighborhood.startswith(location_lower) or result_borough.startswith(location_lower))
            if not location_match:
                diagnosis["diagnostics"].append({
                    "type": "parser_problem",
                    "severity": "medium",
                    "message": f"Top result doesn't match parsed location intent: {location_label}",
                    "parsed_location": location_label,
                    "result_location": f"{top_result.get('neighborhood')} / {top_result.get('borough')}",
                })

    # Check price matching
    if parsed_query and parsed_query.get("price"):
        expected_price = parsed_query.get("price")
        result_price = top_result.get("price", "")
        if expected_price and result_price and str(expected_price).lower() != str(result_price).lower():
            diagnosis["diagnostics"].append({
                "type": "ranker_weighting_problem",
                "severity": "low",
                "message": f"Price mismatch but still ranked top",
                "parsed_price": expected_price,
                "result_price": result_price,
            })

    # Check data coverage
    if not top_result.get("address") or not top_result.get("borough"):
        diagnosis["diagnostics"].append({
            "type": "data_coverage_problem",
            "severity": "medium",
            "message": "Top result missing address or borough information",
        })

    # Check for reasonable fallback
    if top_semantic_score < 0.2 and not diagnosis["diagnostics"]:
        diagnosis["diagnostics"].append({
            "type": "reasonable_fallback",
            "severity": "info",
            "message": "Low semantic score but still returned reasonable result (likely fallback)",
            "semantic_score": top_semantic_score,
        })

    return diagnosis


def main():
    logger.info("Starting NearBite diagnostic evaluation")
    logger.info(f"Test user: {TEST_USER_ID}")
    logger.info(f"Number of queries: {len(TEST_QUERIES)}")

    # Setup test_user_11 if needed
    logger.info(f"\nSetting up test user: {TEST_USER_ID}")
    existing_user = find_user_by_username(TEST_USER_ID)
    if not existing_user:
        create_user(
            username=TEST_USER_ID,
            email=f"{TEST_USER_ID}@nearbite.test",
            password="test1234",
            display_name="Thai food enthusiast"
        )
        logger.info(f"Created new user: {TEST_USER_ID}")
    else:
        logger.info(f"User {TEST_USER_ID} already exists")

    # Create user profile for Thai food preferences
    thai_profile_payload = {
        "top_cuisines": ["Thai"],
        "craving_preferences": ["spicy", "comfort food"],
        "price_comfort_level": "$$",
        "vibes_dining_style": ["casual hangout", "lively / buzzy"],
        "dietary_restrictions": ["None"],
        "adventurousness": 3,
        "travel_willingness": "Short commute (10–20 min / ~1 mi)",
        "dining_company": "Small group (3–5)",
        "typical_meals": ["lunch", "dinner"],
        "decision_criteria": ["ratings", "vibe/atmosphere"],
        "novelty_preference": "mix of both",
        "favorite_dishes": ["pad thai", "tom yum", "green curry"],
        "loved_restaurants": [],
        "wishlist_restaurants": [],
        "frequent_restaurants": [],
        "aspirational_restaurants": [],
    }
    save_user_profile(TEST_USER_ID, thai_profile_payload)
    logger.info(f"Saved profile for {TEST_USER_ID}")

    # Load all restaurants for context
    all_restaurants = load_restaurants()
    logger.info(f"Loaded {len(all_restaurants)} restaurants")

    # Load user profile
    user_profile = get_user_profile(TEST_USER_ID)
    if not user_profile:
        logger.warning(f"No user profile found for {TEST_USER_ID} - will use anonymous")
    else:
        logger.info(f"Loaded profile for {TEST_USER_ID}")
        logger.info(f"Profile text: {user_profile.get('profile_text', '')[:200]}...")

    # Run diagnostics
    all_diagnostics = []
    query_results = {}

    for query in TEST_QUERIES:
        logger.info(f"\n{'='*60}")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*60}")

        try:
            # Parse query
            parsed_query = parse_query(query)
            logger.info(f"Parsed query: {json.dumps(parsed_query, indent=2, default=str)}")

            # Run search through full pipeline
            results = search_restaurants(
                query=query,
                filters=None,
                user_id=TEST_USER_ID,
                top_k=3,
                user_vector_only=False,
            )

            logger.info(f"Retrieved {len(results)} results")

            # Extract diagnostic info
            diagnostic = extract_diagnostic_info(query, results, parsed_query)
            all_diagnostics.append(diagnostic)
            query_results[query] = results

            # Log top 3 results
            for result_info in diagnostic["top_3_results"]:
                logger.info(f"\n  Rank #{result_info['rank']}: {result_info['restaurant_name']}")
                logger.info(f"    Categories: {result_info['categories']}")
                logger.info(f"    Location: {result_info['neighborhood']} / {result_info['borough']}")
                logger.info(f"    Distance: {result_info['distance_km']:.2f} km ({result_info['travel_minutes']} min)")
                logger.info(f"    Final Score: {result_info['final_score']:.4f}")
                logger.info(f"    Semantic Score: {result_info['semantic_score']:.4f}")
                if result_info.get("max_score_contributor"):
                    logger.info(f"    Max Contributor: {result_info['max_score_contributor']['component']} ({result_info['max_score_contributor']['value']:.4f})")

            # Diagnose
            diagnosis = diagnose_result(query, parsed_query, results, all_restaurants)
            if diagnosis["diagnostics"]:
                logger.warning(f"DIAGNOSTICS for '{query}':")
                for diag in diagnosis["diagnostics"]:
                    logger.warning(f"  [{diag['type']}] {diag['message']}")

        except Exception as e:
            logger.exception(f"Error processing query: {query}")
            all_diagnostics.append({
                "query": query,
                "error": str(e),
            })

    # Save results to file
    output_file = PROJECT_ROOT / "testing" / "diagnostic_run_results.json"
    with open(output_file, "w") as f:
        json.dump(all_diagnostics, f, indent=2, default=str)
    logger.info(f"\nDiagnostic results saved to {output_file}")

    return all_diagnostics, query_results


if __name__ == "__main__":
    all_diagnostics, query_results = main()
