"""
recommendation/algorithm.py
Owner: Jonas Chen

Responsibilities:
- Builds user features from questionnaire answers and wrapped signals
- Computes questionnaire-based and wrapped-based restaurant scores
- Produces a final personalized ranking for restaurant recommendation
- Returns a top-k ranked list for display in the frontend
"""

from __future__ import annotations

from recommendation.utils import price_level_value


def build_user_features(questionnaire_answers: dict, wrapped_stats: dict) -> dict:
    """
    Combine questionnaire answers and wrapped summary into one user feature object.

    Why this function exists:
    - The questionnaire captures what the user *says* they like.
    - Wrapped captures what the user *actually interacts with*.
    - The recommendation algorithm should use both.

    Input:
    - questionnaire_answers: saved answers from onboarding / edited questionnaire
    - wrapped_stats: summary built from saved restaurants + interaction history

    Output:
    - A single merged user feature dictionary used by downstream scoring functions.
    """
    return {
        # Questionnaire-based explicit preferences
        "favorite_cuisines": questionnaire_answers.get("favorite_cuisines", []),
        "cravings": questionnaire_answers.get("cravings", []),
        "price_range": questionnaire_answers.get("price_range", "moderate"),
        "place_types": questionnaire_answers.get("place_types", []),
        "dietary": questionnaire_answers.get("dietary", []),
        "usual_location": questionnaire_answers.get("usual_location", ""),
        "meals": questionnaire_answers.get("meals", []),
        "decision_style": questionnaire_answers.get("decision_style", []),
        "novelty_preference": questionnaire_answers.get("novelty_preference", ""),
        "favorite_dishes": questionnaire_answers.get("favorite_dishes", []),
        "frequent_restaurants": questionnaire_answers.get("frequent_restaurants", []),
        "dream_restaurants": questionnaire_answers.get("dream_restaurants", []),

        # Wrapped-based implicit preferences
        "wrapped_top_cuisines": wrapped_stats.get("top_cuisines", []),
        "wrapped_top_boroughs": wrapped_stats.get("top_boroughs", []),
        "wrapped_top_vibes": wrapped_stats.get("top_vibes", []),
        "wrapped_saved_count": wrapped_stats.get("saved_count", 0),
    }


def compute_questionnaire_score(restaurant: dict, user_features: dict) -> float:
    """
    Compute a rule-based score from questionnaire answers.

    High-level idea:
    This score measures how well a restaurant matches what the user explicitly
    wrote in the onboarding questionnaire.

    Scoring signals used here:
    1. Cuisine match
    2. Place / vibe match
    3. Dietary match
    4. Meal match
    5. Favorite dish text match
    6. Price mismatch penalty
    7. Rating bonus
    8. Novelty preference adjustment
    9. Location preference bonus

    This is intentionally simple and interpretable:
    every contribution is manually weighted so that it is easy to debug
    and explain during presentation.
    """
    score = 0.0

    # Pull restaurant fields we need for matching.
    categories = restaurant.get("categories", [])
    borough = restaurant.get("borough", "")
    price = restaurant.get("price", "")
    rating = float(restaurant.get("rating", 0.0) or 0.0)

    # Build one lowercase text blob so we can do quick keyword checks
    # against name / snippet / categories.
    restaurant_text = " ".join(
        [
            restaurant.get("name", ""),
            restaurant.get("review_snippet", ""),
            " ".join(categories[:3]),
        ]
    ).lower()

    # Pull user preference signals.
    favorite_cuisines = user_features.get("favorite_cuisines", [])
    place_types = user_features.get("place_types", [])
    dietary = user_features.get("dietary", [])
    meals = user_features.get("meals", [])
    favorite_dishes = user_features.get("favorite_dishes", [])
    novelty_preference = user_features.get("novelty_preference", "")
    price_range = user_features.get("price_range", "moderate")

    # ---------------------------------------------------------
    # 1. Cuisine match
    # Strong positive signal because cuisine preference is usually
    # one of the clearest restaurant choice indicators.
    # ---------------------------------------------------------
    for cuisine in favorite_cuisines:
        if cuisine in categories:
            score += 4.0

    # ---------------------------------------------------------
    # 2. Place / vibe match
    # If the user likes "cozy", "quiet", "trendy", etc., and the
    # restaurant text appears to mention those signals, add a bonus.
    # ---------------------------------------------------------
    for vibe in place_types:
        if vibe.lower() in restaurant_text:
            score += 2.0

    # ---------------------------------------------------------
    # 3. Dietary match
    # Skip "none", because it means there is no dietary restriction.
    # Otherwise reward restaurants whose text suggests they support
    # the user's dietary preference.
    # ---------------------------------------------------------
    for restriction in dietary:
        if restriction.lower() == "none":
            continue
        if restriction.lower() in restaurant_text:
            score += 2.0

    # ---------------------------------------------------------
    # 4. Meal match
    # If the user says they often go out for brunch / dinner / late night,
    # reward restaurants whose text seems related to those meal contexts.
    # ---------------------------------------------------------
    for meal in meals:
        if meal.lower() in restaurant_text:
            score += 1.0

    # ---------------------------------------------------------
    # 5. Favorite dish match
    # If a user mentions dishes they love, reward restaurants whose
    # text or snippet includes those dishes.
    # ---------------------------------------------------------
    for dish in favorite_dishes:
        if dish.lower() in restaurant_text:
            score += 2.0

    # ---------------------------------------------------------
    # 6. Price mismatch penalty
    # The farther the restaurant price is from the user's preferred
    # price level, the more we subtract.
    #
    # Example:
    # user wants "$$" (2), restaurant is "$$$$" (4)
    # penalty = |2 - 4| * 0.8 = 1.6
    # ---------------------------------------------------------
    target_price = price_level_value(price_range) or 2.0
    restaurant_price_level = price_level_value(price) or 2.0
    score -= abs(target_price - restaurant_price_level) * 0.8

    # ---------------------------------------------------------
    # 7. Rating bonus
    # Add a moderate bonus so very low-rated places do not dominate,
    # but rating does not overwhelm personal preference.
    # ---------------------------------------------------------
    score += rating * 0.6

    # ---------------------------------------------------------
    # 8. Novelty preference adjustment
    #
    # "stick to what i know":
    #   prefer restaurants in cuisines already explicitly liked
    #
    # "try new things":
    #   reward restaurants outside the user's usual favorite cuisines
    # ---------------------------------------------------------
    if novelty_preference == "stick to what i know":
        if any(cuisine in categories for cuisine in favorite_cuisines):
            score += 1.5

    if novelty_preference == "try new things":
        if not any(cuisine in categories for cuisine in favorite_cuisines):
            score += 1.0

    # ---------------------------------------------------------
    # 9. Location preference bonus
    # This is a simple demo assumption:
    # if the user usually eats near school/work, Manhattan gets a small
    # boost because this app is NYC-focused and that is a common center.
    # ---------------------------------------------------------
    if borough and user_features.get("usual_location") == "near school/work":
        if borough == "Manhattan":
            score += 0.7

    return score


def compute_wrapped_score(restaurant: dict, user_features: dict) -> float:
    """
    Compute a lightweight personalization boost from wrapped-style history.

    High-level idea:
    The questionnaire captures stated preference.
    Wrapped captures behavioral preference.

    This function adds a smaller boost based on:
    - cuisines the user has saved / interacted with most
    - boroughs the user tends to save
    - vibes inferred from past behavior

    Compared with questionnaire score, wrapped score is intentionally lighter,
    because history should refine the ranking rather than completely dominate it.
    """
    score = 0.0

    categories = restaurant.get("categories", [])
    borough = restaurant.get("borough", "")

    restaurant_text = " ".join(
        [
            restaurant.get("name", ""),
            restaurant.get("review_snippet", ""),
            " ".join(categories[:3]),
        ]
    ).lower()

    # ---------------------------------------------------------
    # 1. Wrapped top cuisines
    # If the restaurant matches cuisines the user repeatedly saved or viewed,
    # add a behavior-based boost.
    # ---------------------------------------------------------
    for cuisine in user_features.get("wrapped_top_cuisines", []):
        if cuisine in categories:
            score += 1.8

    # ---------------------------------------------------------
    # 2. Wrapped top boroughs
    # If the user often saves restaurants in a specific borough,
    # boost restaurants in that borough.
    # ---------------------------------------------------------
    for favorite_borough in user_features.get("wrapped_top_boroughs", []):
        if borough == favorite_borough:
            score += 1.2

    # ---------------------------------------------------------
    # 3. Wrapped top vibes
    # Similar to questionnaire vibe matching, but based on repeated
    # past behavior instead of explicit answers.
    # ---------------------------------------------------------
    for vibe in user_features.get("wrapped_top_vibes", []):
        if vibe.lower() in restaurant_text:
            score += 1.0

    return score


def recommend_top_restaurants(
    restaurants: list[dict],
    questionnaire_answers: dict,
    wrapped_stats: dict,
    top_k: int = 10,
) -> list[dict]:
    """
    Produce a top-k ranked restaurant list.

    Full pipeline:
    1. Merge questionnaire + wrapped data into one user feature profile
    2. Score every restaurant with:
       - questionnaire_score
       - wrapped_score
    3. Add the two scores to get final_score
    4. Sort descending by final_score
    5. Return the top_k restaurants

    Notes:
    - This is a sample transparent algorithm, not a black-box model.
    - The goal is explainability and reasonable personalization.
    - The frontend can also display component scores for debugging or demo.
    """
    user_features = build_user_features(questionnaire_answers, wrapped_stats)

    ranked: list[dict] = []

    for restaurant in restaurants:
        # Copy so we do not mutate the original input list in place.
        item = dict(restaurant)

        questionnaire_score = compute_questionnaire_score(item, user_features)
        wrapped_score = compute_wrapped_score(item, user_features)

        # Final score is a simple additive combination.
        final_score = questionnaire_score + wrapped_score

        # Store component scores so they are available for debugging,
        # analysis, or UI display.
        item["questionnaire_score"] = questionnaire_score
        item["wrapped_score"] = wrapped_score
        item["final_score"] = final_score

        ranked.append(item)

    # Sort best-first.
    ranked.sort(key=lambda item: item["final_score"], reverse=True)

    # Only return the top requested results.
    return ranked[:top_k]
