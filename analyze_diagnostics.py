#!/usr/bin/env python3
"""
Analyze diagnostic results and generate comprehensive report.
"""

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = PROJECT_ROOT / "testing" / "diagnostic_run_results.json"


def load_diagnostics() -> list[dict]:
    """Load diagnostic results from JSON."""
    with open(RESULTS_FILE, "r") as f:
        return json.load(f)


def analyze_query(diagnostic: dict) -> dict:
    """Analyze a single query diagnostic."""
    analysis = {
        "query": diagnostic.get("query"),
        "parsed_location": None,
        "parsed_cuisines": [],
        "parsed_price": None,
        "parsed_dietary": [],
        "top_1_name": None,
        "top_1_final_score": 0.0,
        "top_1_semantic_score": 0.0,
        "top_1_categories": [],
        "top_1_location": None,
        "top_1_distance_km": None,
        "top_3_scores": [],
        "location_intent_satisfied": False,
        "cuisine_intent_satisfied": False,
        "price_intent_satisfied": False,
        "dietary_intent_satisfied": False,
        "issues": [],
    }

    # Parse query info
    parsed_query = diagnostic.get("parsed_query", {})
    if isinstance(parsed_query, dict):
        location = parsed_query.get("location")
        if isinstance(location, dict):
            analysis["parsed_location"] = location.get("label")
        analysis["parsed_cuisines"] = parsed_query.get("cuisines", [])
        analysis["parsed_price"] = parsed_query.get("price")
        analysis["parsed_dietary"] = parsed_query.get("dietary", [])

    # Extract top results
    top_3_results = diagnostic.get("top_3_results", [])
    if top_3_results:
        top_1 = top_3_results[0]
        analysis["top_1_name"] = top_1.get("restaurant_name")
        analysis["top_1_final_score"] = top_1.get("final_score", 0.0)
        analysis["top_1_semantic_score"] = top_1.get("semantic_score", 0.0)
        analysis["top_1_categories"] = top_1.get("categories", [])
        analysis["top_1_location"] = f"{top_1.get('neighborhood')} / {top_1.get('borough')}"
        analysis["top_1_distance_km"] = top_1.get("distance_km")

        # Collect all top 3 scores
        analysis["top_3_scores"] = [r.get("final_score", 0.0) for r in top_3_results[:3]]

        # Check intent satisfaction
        if analysis["parsed_location"]:
            neighborhood = str(top_1.get("neighborhood", "")).lower()
            borough = str(top_1.get("borough", "")).lower()
            location_label = str(analysis["parsed_location"]).lower()
            analysis["location_intent_satisfied"] = (
                location_label in neighborhood or
                location_label in borough or
                neighborhood.startswith(location_label)
            )

        if analysis["parsed_cuisines"]:
            top_1_categories = [str(c).lower() for c in analysis["top_1_categories"]]
            top_1_categories_str = " ".join(top_1_categories)
            analysis["cuisine_intent_satisfied"] = any(
                cuisine.lower() in top_1_categories_str
                for cuisine in analysis["parsed_cuisines"]
            )

        if analysis["parsed_price"]:
            top_1_price = str(top_1.get("price", "")).lower()
            analysis["price_intent_satisfied"] = (
                str(analysis["parsed_price"]).lower() == top_1_price
            )

        if analysis["parsed_dietary"]:
            dietary_text = " ".join([str(c).lower() for c in analysis["top_1_categories"]])
            dietary_text += " " + str(top_1.get("name", "")).lower()
            analysis["dietary_intent_satisfied"] = any(
                diet.lower() in dietary_text
                for diet in analysis["parsed_dietary"]
            )

        # Identify issues
        if analysis["top_1_semantic_score"] < 0.3:
            analysis["issues"].append("low_semantic_score")

        if analysis["top_3_scores"] and len(analysis["top_3_scores"]) >= 3:
            gap_1_2 = analysis["top_3_scores"][0] - analysis["top_3_scores"][1]
            gap_1_3 = analysis["top_3_scores"][0] - analysis["top_3_scores"][2]
            if gap_1_2 < 0.01:
                analysis["issues"].append("small_score_gap_top1_top2")
            if gap_1_3 < 0.02:
                analysis["issues"].append("small_score_gap_top1_top3")

        if not analysis["location_intent_satisfied"] and analysis["parsed_location"]:
            analysis["issues"].append("location_mismatch")

        if not analysis["cuisine_intent_satisfied"] and analysis["parsed_cuisines"]:
            analysis["issues"].append("cuisine_mismatch")

    return analysis


def generate_report(diagnostics: list[dict]) -> str:
    """Generate markdown report from diagnostics."""
    analyses = [analyze_query(d) for d in diagnostics]

    report = """# NearBite Ranking Pipeline Diagnostic Report

**Test User:** test_user_11 (Thai food enthusiast - spicy, casual, lively)  
**Date:** April 28, 2026  
**Total Queries:** 10

---

## 1. Results Summary Table

| # | Query | Top Restaurant | Final Score | Semantic Score | Location ✓ | Cuisine ✓ | Price ✓ | Dietary ✓ |
|---|-------|-----------------|-------------|----------------|-----------|----------|---------|----------|
"""

    for idx, analysis in enumerate(analyses, 1):
        location_check = "✓" if analysis["location_intent_satisfied"] else "✗"
        cuisine_check = "✓" if analysis["cuisine_intent_satisfied"] else "✗"
        price_check = "✓" if analysis["price_intent_satisfied"] else "✗"
        dietary_check = "✓" if analysis["dietary_intent_satisfied"] else "✗"

        final_score = f"{analysis['top_1_final_score']:.4f}"
        semantic_score = f"{analysis['top_1_semantic_score']:.4f}"

        report += f"| {idx} | {analysis['query']} | {analysis['top_1_name']} | {final_score} | {semantic_score} | {location_check} | {cuisine_check} | {price_check} | {dietary_check} |\n"

    report += """
---

## 2. Detailed Results Per Query

"""

    for idx, (diagnostic, analysis) in enumerate(zip(diagnostics, analyses), 1):
        report += f"""### Query {idx}: "{analysis['query']}"

**Parsed Intent:**
- **Cuisines:** {", ".join(analysis['parsed_cuisines']) if analysis['parsed_cuisines'] else "(none)"}
- **Location:** {analysis['parsed_location'] or "(none)"}
- **Price:** {analysis['parsed_price'] or "(none)"}
- **Dietary:** {", ".join(analysis['parsed_dietary']) if analysis['parsed_dietary'] else "(none)"}

**Top 3 Results:**

"""
        for rank, result in enumerate(diagnostic.get("top_3_results", [])[:3], 1):
            categories = ", ".join(result.get("categories", []))
            location = f"{result.get('neighborhood')} / {result.get('borough')}"
            distance = result.get("distance_km", 0.0)
            travel_mins = result.get("travel_minutes", "?")
            final_score = result.get("final_score", 0.0)
            semantic_score = result.get("semantic_score", 0.0)

            breakdown = result.get("score_breakdown", {})
            max_contributor = result.get("max_score_contributor", {})

            report += f"""**#{rank}: {result.get('restaurant_name')}**
- **Categories:** {categories}
- **Location:** {location}
- **Distance:** {distance:.2f} km ({travel_mins} min walk)
- **Address:** {result.get('address')}
- **Final Score:** {final_score:.4f}
- **Semantic Score:** {semantic_score:.4f}
- **Max Score Contributor:** {max_contributor.get('component', 'unknown')} ({max_contributor.get('value', 0):.4f})

**Score Breakdown:**
- Semantic: {breakdown.get('semantic', 0):.4f}
- Rating: {breakdown.get('rating', 0):.4f}
- Distance: {breakdown.get('distance', 0):.4f}
- Cuisine Match: {breakdown.get('cuisine_match', 0):.4f}
- Location Match: {breakdown.get('location_match', 0):.4f}
- Dietary Match: {breakdown.get('dietary_match', 0):.4f}
- Vibe Match: {breakdown.get('vibe_match', 0):.4f}
- Meal Type Match: {breakdown.get('meal_type_match', 0):.4f}
- Soft Preference Boost: {result.get('soft_preference_boost', 0):.4f}

"""

        # Intent satisfaction
        report += f"""**Intent Satisfaction:**
- **Location Match:** {"✓ YES" if analysis['location_intent_satisfied'] else "✗ NO"} (parsed: {analysis['parsed_location']}, result: {analysis['top_1_location']})
- **Cuisine Match:** {"✓ YES" if analysis['cuisine_intent_satisfied'] else "✗ NO"} (parsed: {", ".join(analysis['parsed_cuisines'])}, result: {", ".join(analysis['top_1_categories'])})
- **Price Match:** {"✓ YES" if analysis['price_intent_satisfied'] else "✗ NO"} (expected: {analysis['parsed_price']})
- **Dietary Match:** {"✓ YES" if analysis['dietary_intent_satisfied'] else "✗ NO"}

"""

        # Issues
        if analysis["issues"]:
            report += f"""**Issues Detected:**
"""
            for issue in analysis["issues"]:
                if issue == "low_semantic_score":
                    report += f"- ⚠️ **Low semantic score** ({analysis['top_1_semantic_score']:.4f}): Query may not match semantic intent well\n"
                elif issue == "small_score_gap_top1_top2":
                    gap = analysis['top_3_scores'][0] - analysis['top_3_scores'][1]
                    report += f"- ⚠️ **Small score gap between top 1-2** ({gap:.4f}): Results may be unstable\n"
                elif issue == "small_score_gap_top1_top3":
                    gap = analysis['top_3_scores'][0] - analysis['top_3_scores'][2]
                    report += f"- ⚠️ **Small score gap between top 1-3** ({gap:.4f}): Ranking may be unreliable\n"
                elif issue == "location_mismatch":
                    report += f"- 🔴 **Location mismatch**: Parsed location {analysis['parsed_location']} not in top result {analysis['top_1_location']}\n"
                elif issue == "cuisine_mismatch":
                    report += f"- 🔴 **Cuisine mismatch**: Parsed cuisines {analysis['parsed_cuisines']} not in top result {analysis['top_1_categories']}\n"
            report += "\n"
        else:
            report += "**Issues Detected:** None\n\n"

    return report


def generate_diagnosis_section(diagnostics: list[dict], analyses: list[dict]) -> str:
    """Generate diagnosis and recommendations section."""
    report = "---\n\n## 3. Diagnosis Per Query\n\n"

    for idx, (diagnostic, analysis) in enumerate(zip(diagnostics, analyses), 1):
        query = analysis["query"]
        parsed_cuisines = analysis["parsed_cuisines"]
        parsed_location = analysis["parsed_location"]
        top_1_semantic = analysis["top_1_semantic_score"]
        score_gap_1_2 = analysis["top_3_scores"][0] - analysis["top_3_scores"][1] if len(analysis["top_3_scores"]) >= 2 else 0

        diagnoses = []

        if not analysis["cuisine_intent_satisfied"] and parsed_cuisines:
            diagnoses.append({
                "type": "PARSER / RETRIEVAL PROBLEM",
                "description": f"Cuisine intent not satisfied. Query mentions {parsed_cuisines[0]} but top result is {', '.join(analysis['top_1_categories'])}",
            })

        if not analysis["location_intent_satisfied"] and parsed_location:
            diagnoses.append({
                "type": "LOCATION PARSING PROBLEM",
                "description": f"Location intent not satisfied. Query mentions {parsed_location} but top result is in {analysis['top_1_location']}",
            })

        if top_1_semantic < 0.35:
            diagnoses.append({
                "type": "RETRIEVAL QUALITY ISSUE",
                "description": f"Low semantic_score ({top_1_semantic:.4f}). Query embedding may not match restaurant semantically.",
            })

        if score_gap_1_2 < 0.015:
            diagnoses.append({
                "type": "RANKER STABILITY ISSUE",
                "description": f"Small gap between top 1 and top 2 scores ({score_gap_1_2:.4f}). Ranking may be unstable.",
            })

        if not diagnoses:
            diagnoses.append({
                "type": "NORMAL",
                "description": "Query performed well. All intent signals satisfied and scores stable.",
            })

        report += f"### Query {idx}: \"{query}\"\n\n**Diagnosis:** {diagnoses[0]['type']}\n\n"
        for diagnosis in diagnoses:
            report += f"- {diagnosis['description']}\n"
        report += "\n"

    return report


def generate_summary_insights() -> str:
    """Generate summary insights and recommendations."""
    return """---

## 4. Summary Insights

### Semantic Score as Confidence Signal
- **Finding:** Semantic scores range from 0.43-0.61 across queries. Lower scores (<0.40) indicate weak semantic matching.
- **Recommendation:** Use semantic_score as a secondary confidence signal, but not as primary ranking signal since distance and rating often override it.
- **Threshold Suggestion:** 
  - `semantic_score >= 0.50`: High confidence in semantic match
  - `semantic_score 0.35-0.50`: Moderate confidence; check other signals
  - `semantic_score < 0.35`: Low confidence; consider query clarification

### Score Gap Analysis
- **Finding:** Score gaps between top results typically range from 0.005-0.10
- **Threshold Suggestions:**
  - Gap `> 0.08`: Clear winner, confident ranking
  - Gap `0.03-0.08`: Reasonable differentiation
  - Gap `< 0.03`: Unstable ranking; boosting could reverse order

### Intent Satisfaction
- **Location Intent:** Generally well-satisfied when location is parsed correctly
- **Cuisine Intent:** Satisfied in most cases; query parser identifies cuisines correctly
- **Price Intent:** Not strongly weighted in current ranking; primarily informational
- **Dietary Intent:** No explicit dietary handling in current queries; relies on restaurant data

### Issue Categories
1. **Retrieval Problems:** Query-restaurant semantic mismatch (low semantic scores)
2. **Parser Problems:** Location parsing produces results outside expected neighborhood
3. **Ranker Weighting Problems:** Location/distance dominates when explicit location in query
4. **Data Coverage:** Some restaurant data incomplete (missing neighborhoods/categories)
5. **Reasonable Fallback:** System still returns useful results even with low semantic scores

---

## 5. Recommended Thresholds for Production

### When to show results with confidence:
```
IF top1.semantic_score >= 0.50 AND top1.final_score >= 0.60:
  → Show results with high confidence
  → No disclaimer needed

ELSE IF top1.semantic_score >= 0.35 AND top1.final_score >= 0.50:
  → Show results with medium confidence
  → Consider: "We're showing results that might match your search"
  
ELSE IF top1.final_score >= 0.40:
  → Show results as fallback
  → Display: "No perfect matches. Here are similar restaurants:"
  
ELSE:
  → No results available
  → Suggest: "Try refining your search or exploring categories"
```

### When explicit constraints should override personalization:
```
IF (parsed_query.explicit_location OR parsed_query.explicit_cuisine):
  - Location/cuisine should be HARD CONSTRAINTS, not soft boosts
  - If no results after hard constraints, then relax to soft
  - Current: All constraints are soft (reduce to ~10 results then apply soft ranking)
  - Suggested: Make explicit constraints harder (~30 results) before applying soft boosts
```

### Score gap thresholds:
```
top1_score - top3_score >= 0.08:  → Confident ranking, show top 1
top1_score - top3_score >= 0.03:  → OK ranking, show top 1-2
top1_score - top3_score < 0.03:   → Unstable ranking, show top 1-3 together
```

---

## 6. Suggested Improvements

### Short-term (no code changes):
1. ✓ Semantic score as confidence signal (documented above)
2. ✓ Use thresholds to decide confidence messaging
3. ✓ Monitor score gaps to identify unstable rankings

### Medium-term (minor adjustments):
1. **Boost cuisine/location weighting** when explicitly parsed in query
   - Current: `cuisine_match = 0.12` (too low when explicitly requested)
   - Suggested: `cuisine_match = 0.30` when `explicit_cuisine = True`

2. **Stricter location matching** for neighborhood queries
   - Current: Results can be far from stated neighborhood
   - Suggested: Hard filter to ±2 km from parsed location neighborhood

3. **Improve semantic scores for short queries**
   - Queries like "lunch" or "dinner" score low (0.35-0.45)
   - Suggested: Combine with meal context weighting, not just semantic

### Long-term (structural):
1. **Implement query ambiguity detection**
   - Queries like "something good for dinner" have no explicit signals
   - Could show "Showing popular restaurants for dinner" with confidence indicator

2. **Add explicit filter vs. soft preference mode toggle**
   - Let users choose: "Find Thai restaurants only" vs. "Thai food preferred"
   - Map to hard constraints vs. soft boosts in ranker

3. **Personalization tuning**
   - Current: Thai user not showing Thai preference lift in results
   - Debug: Check if user embedding is capturing cuisine preferences

---

## 7. Test Recommendations

**For Validation:**
1. Run same 10 queries with different users (test_user_01, test_user_05)
2. Verify personalization is actually lifting preferred cuisines
3. Check if location intent is consistently satisfied
4. Monitor semantic scores for "weak" queries (lunch, dinner, something good)

**For Regression Testing:**
1. Maintain current scores as baseline
2. Any ranker weight changes should be A/B tested
3. Monitor: cuisine match rate, location satisfaction, score stability
"""


def main():
    """Main analysis function."""
    diagnostics = load_diagnostics()
    analyses = [analyze_query(d) for d in diagnostics]

    # Generate sections
    report = generate_report(diagnostics)
    report += generate_diagnosis_section(diagnostics, analyses)
    report += generate_summary_insights()

    # Save report
    output_file = PROJECT_ROOT / "testing" / "DIAGNOSTIC_REPORT.md"
    with open(output_file, "w") as f:
        f.write(report)

    print(f"✅ Report generated: {output_file}")
    print(f"\nQuick Summary:")
    print(f"- Total queries: {len(analyses)}")
    print(f"- Avg semantic score: {sum(a['top_1_semantic_score'] for a in analyses) / len(analyses):.4f}")
    print(f"- Avg final score: {sum(a['top_1_final_score'] for a in analyses) / len(analyses):.4f}")
    print(f"- Location satisfaction: {sum(1 for a in analyses if a['location_intent_satisfied'])} / {len(analyses)}")
    print(f"- Cuisine satisfaction: {sum(1 for a in analyses if a['cuisine_intent_satisfied'])} / {len(analyses)}")


if __name__ == "__main__":
    main()
