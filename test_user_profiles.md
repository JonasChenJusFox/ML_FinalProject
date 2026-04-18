# Synthetic Test User Profiles for Personalization

This file records three intentionally extreme user profiles for manual testing in the Streamlit app.

---

## 1) Cheap casual Asian foodie (student type)

- **username:** `budgetspice_01`
- **password:** `BudgetSpice!2026`

### onboarding_answers

```json
{
  "top_cuisines": ["Japanese", "Korean", "Thai"],
  "craving_preferences": ["comfort food", "spicy", "fast/casual"],
  "price_comfort_level": "$",
  "vibes_dining_style": ["casual hangout", "quick bite / grab-and-go", "late night"],
  "dietary_restrictions": ["None"],
  "adventurousness": 3,
  "travel_willingness": "Short commute (10–20 min / ~1 mi)",
  "dining_company": "Small group (3–5)",
  "typical_meals": ["lunch", "dinner", "late night"],
  "decision_criteria": ["ratings", "convenience", "recommendations"],
  "novelty_preference": "mix of both",
  "favorite_dishes": ["spicy miso ramen", "tteokbokki", "pad kra pao", "karaage"],
  "loved_restaurants": ["Tonchin", "BCD Tofu House", "Woorijip"],
  "wishlist_restaurants": ["Jeju Noodle Bar", "Nowon"],
  "frequent_restaurants": ["Ippudo", "Xi'an Famous Foods", "Mamoun's Falafel"],
  "aspirational_restaurants": ["Atomix", "Jua", "Cote"]
}
```

### normalized_features

```json
{
  "cuisine_pref": ["japanese", "korean", "thai"],
  "craving_tags": ["comfort food", "spicy", "fast/casual"],
  "price_level": { "symbol": "$", "numeric": 1 },
  "vibe_tags": ["casual hangout", "quick bite / grab-and-go", "late night"],
  "dietary_tags": [],
  "adventure_level": 0.5,
  "max_travel_km": 1.6,
  "company_tags": ["small group (3–5)"],
  "meal_tags": ["lunch", "dinner", "late night"],
  "decision_weights": { "ratings": 1.0, "convenience": 1.0, "recommendations": 1.0 },
  "novelty_level": 0.5,
  "dish_tags": ["spicy miso ramen", "tteokbokki", "pad kra pao", "karaage"],
  "restaurant_affinity_terms": [
    "tonchin", "bcd tofu house", "woorijip",
    "ippudo", "xi'an famous foods", "mamoun's falafel",
    "jeju noodle bar", "nowon",
    "atomix", "jua", "cote"
  ]
}
```

### profile_text

Student-style cheap eater who wants spicy, fast, casual Asian food near campus. Loves japanese, korean, and thai spots; default mode is quick bite, grab-and-go, and late night eats after classes. Strong keywords: cheap, budget, spicy, comfort food, noodles, late night, casual hangout, convenient. Usually goes for lunch, dinner, and late night with a small group. Picks places by ratings, convenience, and recommendations; short commute only. Favorite dishes include spicy miso ramen, tteokbokki, pad kra pao, and karaage.

---

## 2) Date-night cozy higher-end Italian & wine person

- **username:** `cozyvino_02`
- **password:** `CozyVino!2026`

### onboarding_answers

```json
{
  "top_cuisines": ["Italian", "Mediterranean / Middle Eastern", "Japanese"],
  "craving_preferences": ["fancy/experimental", "heavy/light"],
  "price_comfort_level": "$$$$",
  "vibes_dining_style": ["cozy / intimate", "date night", "quiet / work-friendly", "outdoor / terrace"],
  "dietary_restrictions": ["None"],
  "adventurousness": 2,
  "travel_willingness": "Across the neighborhood (20–35 min)",
  "dining_company": "Partner / couple",
  "typical_meals": ["dinner", "brunch"],
  "decision_criteria": ["vibe/atmosphere", "review", "ratings"],
  "novelty_preference": "stick to what i know",
  "favorite_dishes": ["cacio e pepe", "truffle pasta", "burrata", "osso buco", "tiramisu"],
  "loved_restaurants": ["L'Artusi", "Via Carota", "Marea"],
  "wishlist_restaurants": ["Don Angie", "Rezdora", "Carbone"],
  "frequent_restaurants": ["Il Buco", "Morandi", "Bar Primi"],
  "aspirational_restaurants": ["Masa", "Le Bernardin", "Per Se"]
}
```

### normalized_features

```json
{
  "cuisine_pref": ["italian", "mediterranean / middle eastern", "japanese"],
  "craving_tags": ["fancy/experimental", "heavy/light"],
  "price_level": { "symbol": "$$$$", "numeric": 4 },
  "vibe_tags": ["cozy / intimate", "date night", "quiet / work-friendly", "outdoor / terrace"],
  "dietary_tags": [],
  "adventure_level": 0.25,
  "max_travel_km": 5.0,
  "company_tags": ["partner / couple"],
  "meal_tags": ["dinner", "brunch"],
  "decision_weights": { "vibe/atmosphere": 1.0, "review": 1.0, "ratings": 1.0 },
  "novelty_level": 0.1,
  "dish_tags": ["cacio e pepe", "truffle pasta", "burrata", "osso buco", "tiramisu"],
  "restaurant_affinity_terms": [
    "l'artusi", "via carota", "marea",
    "il buco", "morandi", "bar primi",
    "don angie", "rezdora", "carbone",
    "masa", "le bernardin", "per se"
  ]
}
```

### profile_text

Cozy date-night diner with a strong higher-end Italian and wine-bar bias. Prefers intimate, quiet, romantic rooms with polished service and terrace options. Strong keywords: cozy, date night, upscale, wine, elegant, pasta, refined, intimate atmosphere. Typically goes out for dinner and weekend brunch with partner/couple. Will travel across the neighborhood for quality, but mostly sticks to known favorites. Chooses mainly by vibe, reviews, and ratings; low novelty, high quality threshold.

---

## 3) Adventurous spicy experimental foodie (travels far)

- **username:** `wildpalate_03`
- **password:** `WildPalate!2026`

### onboarding_answers

```json
{
  "top_cuisines": ["Indian", "Mexican", "Thai"],
  "craving_preferences": ["spicy", "fancy/experimental", "fast/casual"],
  "price_comfort_level": "$$$",
  "vibes_dining_style": ["lively / buzzy", "late night", "casual hangout", "outdoor / terrace"],
  "dietary_restrictions": ["None"],
  "adventurousness": 5,
  "travel_willingness": "Anywhere in the city",
  "dining_company": "Solo",
  "typical_meals": ["dinner", "late night", "brunch"],
  "decision_criteria": ["recommendations", "review", "vibe/atmosphere"],
  "novelty_preference": "try new things",
  "favorite_dishes": ["sichuan dry pot", "goat birria", "fermented dosa", "offal tacos", "nashville hot chicken"],
  "loved_restaurants": ["Semma", "Ugly Baby", "Dhamaka"],
  "wishlist_restaurants": ["Foxface Natural", "Aska", "Frevo"],
  "frequent_restaurants": ["Somtum Der", "Birria-Landia", "Szechuan Mountain House"],
  "aspirational_restaurants": ["Atomix", "Atera", "Chef's Table at Brooklyn Fare"]
}
```

### normalized_features

```json
{
  "cuisine_pref": ["indian", "mexican", "thai"],
  "craving_tags": ["spicy", "fancy/experimental", "fast/casual"],
  "price_level": { "symbol": "$$$", "numeric": 3 },
  "vibe_tags": ["lively / buzzy", "late night", "casual hangout", "outdoor / terrace"],
  "dietary_tags": [],
  "adventure_level": 1.0,
  "max_travel_km": 20.0,
  "company_tags": ["solo"],
  "meal_tags": ["dinner", "late night", "brunch"],
  "decision_weights": { "recommendations": 1.0, "review": 1.0, "vibe/atmosphere": 1.0 },
  "novelty_level": 0.9,
  "dish_tags": ["sichuan dry pot", "goat birria", "fermented dosa", "offal tacos", "nashville hot chicken"],
  "restaurant_affinity_terms": [
    "semma", "ugly baby", "dhamaka",
    "somtum der", "birria-landia", "szechuan mountain house",
    "foxface natural", "aska", "frevo",
    "atomix", "atera", "chef's table at brooklyn fare"
  ]
}
```

### profile_text

Highly adventurous foodie profile optimized for novelty, spice, and experimental menus across NYC. Actively seeks new cuisines, chef-driven concepts, and bold flavors including fermented, offal, and very spicy dishes. Strong keywords: adventurous, spicy, experimental, buzzy, late night, new cuisines, destination dining, citywide travel. Travels anywhere in the city, often dines solo, and prioritizes recommendations, deep reviews, and atmosphere over convenience. Prefers lively energy and is comfortable with mid-to-high price points when the food is unique.
