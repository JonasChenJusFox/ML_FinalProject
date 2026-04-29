# NearBite Diagnostic Evaluation - Executive Summary

## Quick Overview

**Diagnostic Run Date:** April 28, 2026  
**Test User:** test_user_11 (Thai food enthusiast - spicy, casual, lively)  
**Queries Tested:** 10 representative queries  
**Report Files:** 
- `testing/DIAGNOSTIC_REPORT.md` - Full comprehensive report
- `testing/diagnostic_run_results.json` - Raw JSON results

---

## Key Metrics at a Glance

| Metric | Result | Assessment |
|--------|--------|------------|
| **Average Semantic Score** | 0.5801 | Moderate (borderline confidence) |
| **Average Final Score** | 0.6834 | Acceptable range |
| **Location Intent Satisfied** | 0/10 (0%) | 🔴 **CRITICAL ISSUE** |
| **Cuisine Intent Satisfied** | 6/10 (60%) | Moderate - room for improvement |
| **Price Intent Satisfied** | 0/10 (0%) | Not weighted in ranking |
| **Dietary Intent Satisfied** | 1/10 (10%) | Minimal support |

---

## Critical Findings

### 🔴 **1. MAJOR LOCATION MATCHING PROBLEM**
- **Issue:** When users specify a neighborhood in their query (e.g., "Italian pasta in West Village"), the top result is frequently in a completely different neighborhood
- **Examples:**
  - Query: "italian pasta in **West Village**" → Result: **Chelsea - Clinton** (not West Village)
  - Query: "mexican tacos in **Lower East Side**" → Result: **Greenpoint, Brooklyn** (far away)
  - Query: "sushi near **SoHo**" → Result: **Chelsea - Clinton** (different neighborhood)
  - Query: "burgers near **10012**" → Result: **Times Square** (different zipcode)
  - Query: "lunch in **Midtown**" → Result: **Chelsea** (adjacent but not Midtown)

**Root Cause:** Location parsing works (neighborhoods are correctly parsed), but they are implemented as **SOFT BOOSTS** (0.13 weight max), not hard constraints. Distance becomes the dominant factor, pulling results from closer alternatives outside the stated location.

**Impact:** Users expect location to be a hard filter, not a preference. This is a **UX violation**.

**Solution:** Make location a hard constraint when explicitly specified in query.

---

### 🟡 **2. SEMANTIC SCORE AS CONFIDENCE SIGNAL - UNRELIABLE**
- **Observation:** Semantic scores range 0.41-0.71, but don't correlate with actual ranking quality
- **Example:** Query "something good for dinner" has a low semantic score (0.4665) but still returns relevant result (Thai Diner)
- **Example:** Query "cheap steakhouse near East Village" has moderate semantic (0.5885) but top result is Australian/Burgers, not steakhouse

**Recommendation:** Semantic score alone is insufficient as confidence signal. Use in combination with:
- Score gap between top results (stability)
- Intent satisfaction checks (location, cuisine, price, dietary)
- Score components breakdown

**Threshold Guidance:**
- `semantic >= 0.50` + `final_score >= 0.60` → High confidence (show as "Top match")
- `semantic 0.35-0.50` + `final_score 0.50-0.60` → Medium confidence (show as "Good match")
- `semantic < 0.35` OR `final_score < 0.50` → Low confidence (show as "Related recommendations")

---

### 🟠 **3. SCORE COMPONENT IMBALANCE**
- **Distance dominates:** In 70% of results, distance is the #1 score contributor (often 0.85-0.93)
- **Semantic underweighted:** Despite 0.60 weight, semantic often ranks #3-4 behind distance and rating
- **Problem:** Closeness overrides relevance. A nearby burger joint scores higher than a precise match 3 km away

**Example - Query 1: "italian pasta in West Village"**
- Top result: Da Andrea (Italian) - Distance dominates with 0.9298 contribution
- Why it won: It's close (0.70 km) even though it's in Chelsea, not West Village
- Cuisine boost was only 0.12, insufficient to overcome distance penalty in other results

**Current Weighting:**
```
DEFAULT_RANKING_WEIGHTS = {
    "semantic": 0.60,
    "rating": 0.10,
    "popularity": 0.05,
    "price_match": 0.05,
    "distance": 0.20,  # But boosted via soft_preference_boost via location_match
}
```

**Issue:** Location is parsed but boosted as soft preference (0.25 * location_match), not hard-coded into distance scoring.

---

### 🟡 **4. QUERY PARSER WORKS, BUT SIGNALS NOT ENFORCED**
- **Parser Performance:** Query parser successfully extracts:
  - ✓ Cuisines (Italian, Mexican, Sushi, etc.)
  - ✓ Locations (West Village, Lower East Side, SoHo, etc.)
  - ✓ Prices (cheap, etc.)
  - ✓ Dietary restrictions (vegan)
  - ✓ Meal types (lunch, dinner, brunch)

- **Problem:** Parsed signals are NOT enforced in ranking
  - Cuisine parsed → but not filtered (only soft +0.12 boost)
  - Location parsed → but not filtered (only soft +0.13 boost)
  - Price parsed → rarely affects ranking
  - Dietary parsed → rarely affects ranking

**Solution:** Explicit constraints should become hard filters:
- If query contains cuisine → retrieve only that cuisine category (hard filter)
- If query contains location → hard filter to neighborhood ±2 km
- If query contains dietary restriction → hard filter
- THEN apply soft personalization on top

---

### 🟢 **5. CUISINE INTENT MOSTLY SATISFIED (60%)**
- **Good News:** When cuisine is the focus, ranking often gets it right
- **Examples:**
  - ✓ "italian pasta" → Italian restaurants at top
  - ✓ "mexican tacos" → Mexican restaurants at top
  - ✓ "sushi" → Sushi restaurants at top
  - ✓ "dessert" → Dessert places at top
  - ✓ "coffee" → Coffee places at top

**Issue:** Location overrides cuisine when both are specified

---

### 🔵 **6. PERSONALIZATION NOT VISIBLE**
- **Test:** test_user_11 has Thai preference but shows mixed results
- **Query 6:** "something good for dinner" returned Thai Diner (good alignment!)
- **However:** No obvious personalization lift from user profile
- **Hypothesis:** User embedding may not be properly capturing cuisine preferences, or alpha blending (0.3) is too low

**Recommendation:** Verify user profile embedding is generated and fused correctly

---

## Actionable Recommendations

### **IMMEDIATE (Do Not Change Code Yet - Just Report)**
1. ✓ Document current scoring behavior (COMPLETED)
2. ✓ Establish confidence thresholds (COMPLETED)
3. ✓ Identify root causes (COMPLETED)

### **SHORT-TERM (No Code Changes Needed)**
1. Add confidence messaging to UI based on semantic_score + intent satisfaction
2. Show location zone in results: "Results near West Village" vs. "Closest restaurants"
3. Monitor score gaps as stability metric in analytics

### **MEDIUM-TERM (Minor Code Changes)**
1. **Implement Hard Location Filtering**
   ```python
   # When explicit location parsed:
   # - Hard filter: Keep only results within 2-3 km of parsed location
   # - Then rank with soft boosts
   # - Current: Only soft +0.13 location boost
   ```

2. **Boost Explicit Cuisine/Diet Constraints**
   ```python
   # When explicit cuisine parsed:
   # - Hard filter: Match category OR use semantic similarity >= 0.65
   # - Current: Only soft +0.12 cuisine boost
   
   # When explicit dietary parsed:
   # - Hard filter: Must match dietary tags
   # - Current: Only soft +0.34-0.42 boost
   ```

3. **Improve Price Weighting**
   ```python
   # Current: price_match only in price_match score (0.05 weight)
   # Suggested: When explicit price parsed, filter first
   # E.g., "cheap steakhouse" -> filter to cheap restaurants, then find steakhouse
   ```

4. **Debug Personalization**
   - Verify user profile embedding captures cuisine preferences
   - Test with explicit Thai query: Should Thai users see more Thai results?
   - Increase alpha blending if personalization is working but underweighted

### **LONG-TERM (Structural)**
1. **Query Intent Confidence Levels**
   - Explicit intent (cuisines, location, diet) → High confidence, use as hard filter
   - Implicit intent (adjectives, mood) → Lower confidence, use as soft boost
   - Ambiguous intent (generic like "dinner") → Fallback to personalization + popularity

2. **Implement Explicit vs. Soft Filter Mode**
   - Let ranker know which are hard constraints vs. soft preferences
   - Current: Everything is soft (passed via `soft_preferences` dict)
   - Suggested: Split into `hard_filters` and `soft_preferences`

---

## Summary Table: Query Performance

| # | Query | Top Result | Semantic | Final | Location | Cuisine | Issue |
|---|-------|-----------|----------|-------|----------|---------|-------|
| 1 | italian pasta in West Village | Da Andrea (Chelsea) | 0.5845 | 0.7302 | ✗ | ✓ | Location mismatch |
| 2 | mexican tacos in Lower East Side | Taqueria (Brooklyn) | 0.6127 | 0.6774 | ✗ | ✓ | Location mismatch |
| 3 | sushi near SoHo | Suki Desu (Chelsea) | 0.6297 | 0.6988 | ✗ | ✓ | Location mismatch |
| 4 | burgers near 10012 | 7th St Burger (Times Sq) | 0.5486 | 0.6335 | ✗ | ✓ | Location mismatch |
| 5 | lunch in Midtown | Liberty Bagels (Chelsea) | 0.6377 | 0.7093 | ✗ | ✗ | Location & category mismatch |
| 6 | something good for dinner | Thai Diner | 0.4665 | 0.5680 | ✓ | ✓ | Normal (generic query) |
| 7 | cheap vegan brunch in Tribeca | Ital Kitchen (Brooklyn) | 0.5075 | 0.7197 | ✗ | ✗ | Location & dietary weak |
| 8 | highly rated dessert in Times Square | Spot Dessert (Union Sq) | 0.7146 | 0.7504 | ✗ | ✓ | Location mismatch |
| 9 | cheap steakhouse near East Village | Little Ruby's (Union Sq) | 0.5885 | 0.6936 | ✗ | ✗ | Location & category mismatch |
| 10 | quick coffee under $5 | Ludlow Coffee | 0.5107 | 0.6531 | ✓ | ✓ | Normal (simple query) |

---

## Conclusion

**Overall Assessment:** The ranking pipeline produces usable results but has **one critical UX problem: location constraints are not enforced**.

**Current State:**
- ✓ Semantic retrieval works
- ✓ Ranking formula is sound
- ✓ Fallback behavior is reasonable
- ✗ Location intent frequently violated (0% satisfaction)
- ⚠️ Personalization impact unclear

**No App Behavior Changes Made:** This is a diagnostic report only. All scoring and ranking remains unchanged.

**Next Steps:**
1. Review this report with product team
2. Decide: Should location be hard filter or soft boost?
3. If hard filter: Implement location hard filtering
4. If soft boost: Add confidence messaging to manage expectations
5. Re-run diagnostics to validate changes

---

## Files Generated

1. **`testing/DIAGNOSTIC_REPORT.md`** (30KB)
   - Complete detailed report with all 10 queries
   - Score breakdowns per result
   - Diagnosis for each query
   - Recommendations and thresholds

2. **`testing/diagnostic_run_results.json`** (41KB)
   - Raw JSON results from all queries
   - Parsed query intent per query
   - Top 3 results with full score details
   - Can be programmatically analyzed

3. **`testing/DIAGNOSTIC_SUMMARY.md`** (this file)
   - Executive summary
   - Key findings and critical issues
   - Actionable recommendations
   - Quick reference metrics

---

## How to Use This Report

1. **For Product Decision:** Use "Actionable Recommendations" section
2. **For Engineering:** Use "DIAGNOSTIC_REPORT.md" for detailed analysis
3. **For QA/Testing:** Use "Summary Table" to validate future changes
4. **For Analytics:** Monitor "Score Gap Thresholds" and semantic scores
