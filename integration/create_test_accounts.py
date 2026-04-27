#!/usr/bin/env python3
"""
scripts/create_test_accounts.py

Generates 25 ready-to-use test accounts with diverse personas.
Safe to rerun: it will reset passwords and overwrite profiles if they already exist.
"""

import sys
from pathlib import Path

# Ensure the script can import from the root project directory
sys.path.append(str(Path(__file__).resolve().parent.parent))

from integration.user_repo import (
    create_user,
    find_user_by_username,
    reset_user_password,
    save_user_profile,
)

PASSWORD = "test1234"

PERSONAS = [
    {
        "id": 1, "name": "Cheap casual Asian food",
        "cuisines": ["Japanese", "Chinese", "Thai"], "price": "$", "vibes": ["casual hangout", "quick bite / grab-and-go"],
        "cravings": ["comfort food", "fast/casual"], "dietary": ["None"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 2, "name": "Vegan healthy food",
        "cuisines": ["Mediterranean / Middle Eastern", "Other"], "price": "$$", "vibes": ["cozy / intimate", "quiet / work-friendly"],
        "cravings": ["heavy/light"], "dietary": ["Vegan"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 3, "name": "Date night Italian",
        "cuisines": ["Italian"], "price": "$$$", "vibes": ["date night", "cozy / intimate", "outdoor / terrace"],
        "cravings": ["comfort food", "fancy/experimental"], "dietary": ["None"], "meals": ["dinner"]
    },
    {
        "id": 4, "name": "Coffee/brunch",
        "cuisines": ["American / Burgers", "Other"], "price": "$$", "vibes": ["casual hangout", "outdoor / terrace"],
        "cravings": ["heavy/light", "sweet/dessert"], "dietary": ["None"], "meals": ["breakfast", "brunch"]
    },
    {
        "id": 5, "name": "Spicy food",
        "cuisines": ["Indian", "Mexican", "Thai"], "price": "$$", "vibes": ["lively / buzzy", "casual hangout"],
        "cravings": ["spicy"], "dietary": ["None"], "meals": ["dinner", "late night"]
    },
    {
        "id": 6, "name": "Dessert/cafe",
        "cuisines": ["Other", "Italian"], "price": "$", "vibes": ["cozy / intimate", "quiet / work-friendly"],
        "cravings": ["sweet/dessert"], "dietary": ["None"], "meals": ["late night"]
    },
    {
        "id": 7, "name": "Mediterranean",
        "cuisines": ["Mediterranean / Middle Eastern"], "price": "$$", "vibes": ["casual hangout", "outdoor / terrace"],
        "cravings": ["heavy/light", "comfort food"], "dietary": ["None"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 8, "name": "Fast lunch near NYU",
        "cuisines": ["American / Burgers", "Mexican", "Other"], "price": "$", "vibes": ["quick bite / grab-and-go"],
        "cravings": ["fast/casual"], "dietary": ["None"], "meals": ["lunch"]
    },
    {
        "id": 9, "name": "Upscale high-rated dinner",
        "cuisines": ["Japanese", "Italian", "Other"], "price": "$$$$", "vibes": ["date night", "cozy / intimate"],
        "cravings": ["fancy/experimental"], "dietary": ["None"], "meals": ["dinner"]
    },
    {
        "id": 10, "name": "No strong preference baseline",
        "cuisines": ["American / Burgers", "Italian", "Chinese"], "price": "$$", "vibes": ["casual hangout"],
        "cravings": ["comfort food"], "dietary": ["None"], "meals": ["dinner"]
    },
    {
        "id": 11, "name": "Thai food",
        "cuisines": ["Thai"], "price": "$$", "vibes": ["casual hangout", "lively / buzzy"],
        "cravings": ["spicy", "comfort food"], "dietary": ["None"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 12, "name": "Korean food",
        "cuisines": ["Korean"], "price": "$$", "vibes": ["lively / buzzy", "late night"],
        "cravings": ["spicy", "comfort food"], "dietary": ["None"], "meals": ["dinner", "late night"]
    },
    {
        "id": 13, "name": "Chinese food",
        "cuisines": ["Chinese"], "price": "$$", "vibes": ["casual hangout", "group friendly" if "group friendly" in "VIBES" else "lively / buzzy"],
        "cravings": ["comfort food", "spicy"], "dietary": ["None"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 14, "name": "Japanese ramen/sushi",
        "cuisines": ["Japanese"], "price": "$$$", "vibes": ["cozy / intimate", "quiet / work-friendly"],
        "cravings": ["comfort food", "heavy/light"], "dietary": ["None"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 15, "name": "Vegetarian",
        "cuisines": ["Indian", "Mediterranean / Middle Eastern", "Mexican"], "price": "$$", "vibes": ["casual hangout", "outdoor / terrace"],
        "cravings": ["comfort food", "heavy/light"], "dietary": ["Vegetarian"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 16, "name": "Burger/comfort food",
        "cuisines": ["American / Burgers"], "price": "$", "vibes": ["casual hangout", "quick bite / grab-and-go"],
        "cravings": ["comfort food", "fast/casual"], "dietary": ["None"], "meals": ["lunch", "dinner", "late night"]
    },
    {
        "id": 17, "name": "Mexican/taco",
        "cuisines": ["Mexican"], "price": "$", "vibes": ["lively / buzzy", "casual hangout", "outdoor / terrace"],
        "cravings": ["spicy", "fast/casual"], "dietary": ["None"], "meals": ["lunch", "dinner"]
    },
    {
        "id": 18, "name": "Indian food",
        "cuisines": ["Indian"], "price": "$$", "vibes": ["cozy / intimate", "casual hangout"],
        "cravings": ["spicy", "comfort food"], "dietary": ["None"], "meals": ["dinner"]
    },
    {
        "id": 19, "name": "Pizza/pasta",
        "cuisines": ["Italian"], "price": "$$", "vibes": ["casual hangout", "lively / buzzy"],
        "cravings": ["comfort food", "fast/casual"], "dietary": ["None"], "meals": ["lunch", "dinner", "late night"]
    },
    {
        "id": 20, "name": "Cheap student",
        "cuisines": ["American / Burgers", "Mexican", "Chinese"], "price": "$", "vibes": ["quick bite / grab-and-go", "late night"],
        "cravings": ["fast/casual", "comfort food"], "dietary": ["None"], "meals": ["lunch", "late night"]
    },
    {
        "id": 21, "name": "Trendy aesthetic cafe",
        "cuisines": ["Japanese", "Other"], "price": "$$$", "vibes": ["cozy / intimate", "outdoor / terrace"],
        "cravings": ["sweet/dessert", "fancy/experimental"], "dietary": ["None"], "meals": ["brunch"]
    },
    {
        "id": 22, "name": "Quiet study spot",
        "cuisines": ["Other", "American / Burgers"], "price": "$", "vibes": ["quiet / work-friendly", "cozy / intimate"],
        "cravings": ["heavy/light", "sweet/dessert"], "dietary": ["None"], "meals": ["breakfast", "lunch"]
    },
    {
        "id": 23, "name": "Group dinner",
        "cuisines": ["Korean", "Mexican", "Italian"], "price": "$$$", "vibes": ["lively / buzzy", "casual hangout"],
        "cravings": ["comfort food", "fancy/experimental"], "dietary": ["None"], "meals": ["dinner"]
    },
    {
        "id": 24, "name": "Late-night food",
        "cuisines": ["Chinese", "Mexican", "American / Burgers"], "price": "$", "vibes": ["late night", "lively / buzzy"],
        "cravings": ["fast/casual", "comfort food", "spicy"], "dietary": ["None"], "meals": ["late night"]
    },
    {
        "id": 25, "name": "Mixed adventurous",
        "cuisines": ["Vietnamese", "Indian", "Mediterranean / Middle Eastern"], "price": "$$$", "vibes": ["lively / buzzy", "date night"],
        "cravings": ["fancy/experimental", "spicy"], "dietary": ["None"], "meals": ["dinner"]
    },
]


def build_questionnaire_payload(persona: dict) -> dict:
    """Construct a full onboarding payload from the minimal persona definition."""
    # Defaults
    payload = {
        "top_cuisines": persona["cuisines"],
        "craving_preferences": persona["cravings"],
        "price_comfort_level": persona["price"],
        "vibes_dining_style": persona["vibes"],
        "dietary_restrictions": persona["dietary"],
        "adventurousness": 5 if "adventurous" in persona["name"].lower() else 3,
        "travel_willingness": "Short commute (10–20 min / ~1 mi)",
        "dining_company": "Small group (3–5)",
        "typical_meals": persona["meals"],
        "decision_criteria": ["ratings", "vibe/atmosphere"],
        "novelty_preference": "mix of both",
        "favorite_dishes": [],
        "loved_restaurants": [],
        "wishlist_restaurants": [],
        "frequent_restaurants": [],
        "aspirational_restaurants": [],
    }
    
    # Adjustments based on persona name
    name_lower = persona["name"].lower()
    if "group" in name_lower:
        payload["dining_company"] = "Large group (6+)"
    elif "date" in name_lower:
        payload["dining_company"] = "Partner / couple"
    
    if "adventurous" in name_lower:
        payload["novelty_preference"] = "try new things"
        payload["travel_willingness"] = "Anywhere in the city"
    elif "baseline" in name_lower:
        payload["novelty_preference"] = "stick to what i know"

    if "student" in name_lower or "nyu" in name_lower:
        payload["travel_willingness"] = "Walking distance (< 10 min / ~0.5 mi)"
        payload["decision_criteria"] = ["convenience", "ratings"]

    return payload


def main():
    print(f"Creating 25 test accounts. Password for all is: {PASSWORD}")
    
    for persona in PERSONAS:
        idx = persona["id"]
        username = f"test_user_{idx:02d}"
        email = f"{username}@nearbite.test"
        display_name = persona["name"]
        
        # 1. Create or Reset User Account
        existing_user = find_user_by_username(username)
        if existing_user:
            reset_user_password(username, PASSWORD)
            print(f"[{idx:02d}/25] Reset password for existing user: {username}")
        else:
            create_user(
                username=username,
                email=email,
                password=PASSWORD,
                display_name=display_name
            )
            print(f"[{idx:02d}/25] Created new user: {username}")
            
        # 2. Build and Save Profile
        # This will securely write to Mongo or the Local DB fallback,
        # update normalized features, generate the `profile_text`,
        # and handle `upsert=True` properly so we don't get duplicates.
        payload = build_questionnaire_payload(persona)
        save_user_profile(username, payload)
        
    print("\n✅ Successfully created/updated 25 test accounts!")
    print("\nNote: Interaction seeding (saves/likes) was intentionally skipped.")
    print("Seeding interactions safely requires exact business_id's from your local dataset,")
    print("and injecting fake ones could break the map/profile views.")

if __name__ == "__main__":
    main()