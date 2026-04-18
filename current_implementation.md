# Current Personalization Implementation (As Implemented Now)

This document describes what is currently implemented in this repository as of today.

---

## A. What functionality is currently working

### 1) Onboarding -> profile_text -> embedding -> search personalization
- Working path is implemented.
- Onboarding form saves questionnaire answers via:
  - frontend/components/onboarding_form.py -> render_onboarding_form
  - frontend/user_profile_state.py -> save_questionnaire_answers
  - integration/user_repo.py -> save_user_profile
- save_user_profile currently writes:
  - raw_answers
  - normalized_features
  - profile_text
  - latest_embedding
- Search personalization currently reads profile via:
  - integration/api.py -> _build_user_embedding_if_available
- Embedding behavior in _build_user_embedding_if_available:
  1. If latest_embedding.vector exists -> use it
  2. Else if profile_text exists -> embed with embeddings/vectorizer.py -> embed_user, then persist via integration/user_repo.py -> update_latest_embedding
  3. Else -> no user embedding
- Search fusion happens in:
  - integration/api.py -> search_restaurants
  - recommendation/ranker.py -> fuse_vectors

### 2) Fallback behavior
- If user_id is anonymous: no user embedding is used.
- If user_vector_only=True (Discover logged-in mode):
  - with user embedding: query vector is zero-vector and user vector drives retrieval (alpha=1.0)
  - without user embedding: fallback to location+rating ranking in integration/api.py -> _rank_by_location_and_rating
- If user_vector_only=False:
  - query is embedded
  - if user embedding exists, fused with alpha=0.3
  - if no user embedding, effectively query-only search (fuse_vectors returns query vector unchanged)

### 3) Local JSON fallback
- Implemented in integration/db.py.
- If Mongo URI is missing or ping fails, USE_LOCAL_DB=True.
- get_collection then returns local JSON-backed _LocalCollection.
- Local file path used: data/local_db.json (created on first write).

### 4) Synthetic test users
- Implemented as static file:
  - data/synthetic_user_profiles.json
- Loader function exists:
  - data/pipeline.py -> load_synthetic_user_profiles
- Important: synthetic users are not automatically inserted into Mongo/local_db by app startup.

### 5) Remaining limitations
- No embedding history/versioning (intentionally not implemented yet).
- No explicit onboarding “other cuisine text” input field; “Other” exists as an option only.
- Synthetic profiles are available but not wired to auto-seeding.
- ranking/ranker.py personalization logic is not deeply profile-aware; personalization is mainly from fused vector retrieval as requested.
- search_restaurants still passes user_history to rank_candidates, but rank_candidates currently ignores it (existing behavior).

---

## B. Exact current user data format

## 1) Stored user profile document

### Field names and types
- username: string
- raw_answers: object
- normalized_features: object
- profile_text: string
- latest_embedding: object|null
- updated_at: datetime (Mongo) or ISO string (local JSON fallback)

### Example object
```json
{
  "username": "alice",
  "raw_answers": {
    "top_cuisines": ["Japanese", "Thai", "Italian"],
    "craving_preferences": ["spicy", "comfort food"],
    "price_comfort_level": "$$",
    "vibes_dining_style": ["casual hangout", "lively / buzzy"],
    "dietary_restrictions": ["None"],
    "adventurousness": 4,
    "travel_willingness": "Across the neighborhood (20–35 min)",
    "dining_company": "Small group (3–5)",
    "typical_meals": ["dinner", "late night"],
    "decision_criteria": ["ratings", "vibe/atmosphere"],
    "novelty_preference": "mix of both",
    "favorite_dishes": ["ramen", "udon"],
    "loved_restaurants": ["Ippudo"],
    "wishlist_restaurants": ["Atomix"],
    "frequent_restaurants": ["Raku"],
    "aspirational_restaurants": ["Masa"]
  },
  "normalized_features": {
    "cuisine_pref": ["japanese", "thai", "italian"],
    "craving_tags": ["spicy", "comfort food"],
    "price_level": {"symbol": "$$", "numeric": 2},
    "vibe_tags": ["casual hangout", "lively / buzzy"],
    "dietary_tags": [],
    "adventure_level": 0.75,
    "max_travel_km": 5.0,
    "company_tags": ["small group (3–5)"],
    "meal_tags": ["dinner", "late night"],
    "decision_weights": {"ratings": 1.0, "vibe/atmosphere": 1.0},
    "novelty_level": 0.5,
    "dish_tags": ["ramen", "udon"],
    "restaurant_affinity_terms": ["ippudo", "raku", "atomix", "masa"]
  },
  "profile_text": "top_cuisines: Japanese, Thai, Italian | ...",
  "latest_embedding": {
    "vector": [0.01, -0.03, 0.08],
    "model_name": "multi-qa-MiniLM-L6-cos-v1",
    "updated_at": "2026-04-18T..."
  },
  "updated_at": "2026-04-18T..."
}
```

### Where stored
- Mongo collection: user_profiles
- Local fallback: data/local_db.json under key user_profiles

### Which code reads/writes
- write: integration/user_repo.py -> save_user_profile
- read: integration/user_repo.py -> get_user_profile
- embed update write: integration/user_repo.py -> update_latest_embedding

---

## 2) Raw onboarding answers

### Field names and types
- top_cuisines: list[string]
- craving_preferences: list[string]
- price_comfort_level: string ($, $$, $$$, $$$$)
- vibes_dining_style: list[string]
- dietary_restrictions: list[string]
- adventurousness: integer (1..5)
- travel_willingness: string
- dining_company: string
- typical_meals: list[string]
- decision_criteria: list[string]
- novelty_preference: string
- favorite_dishes: list[string]
- loved_restaurants: list[string]
- wishlist_restaurants: list[string]
- frequent_restaurants: list[string]
- aspirational_restaurants: list[string]

### Example object
```json
{
  "top_cuisines": ["Japanese", "Korean", "Thai"],
  "craving_preferences": ["spicy", "fancy/experimental"],
  "price_comfort_level": "$$$",
  "vibes_dining_style": ["lively / buzzy", "date night"],
  "dietary_restrictions": ["None"],
  "adventurousness": 5,
  "travel_willingness": "Anywhere in the city",
  "dining_company": "Partner / couple",
  "typical_meals": ["dinner", "late night"],
  "decision_criteria": ["vibe/atmosphere", "recommendations"],
  "novelty_preference": "try new things",
  "favorite_dishes": ["ramen", "tom yum"],
  "loved_restaurants": ["Ippudo"],
  "wishlist_restaurants": ["Atomix"],
  "frequent_restaurants": ["Raku"],
  "aspirational_restaurants": ["Masa"]
}
```

### Where stored
- profile document field raw_answers
- Streamlit session state key questionnaire_answers

### Which code reads/writes
- write from UI: frontend/components/onboarding_form.py -> render_onboarding_form
- adapter and save: frontend/user_profile_state.py -> save_questionnaire_answers
- persist: integration/user_repo.py -> save_user_profile

---

## 3) Normalized user features

### Field names and types
- cuisine_pref: list[string]
- craving_tags: list[string]
- price_level: object {symbol: string, numeric: integer}
- vibe_tags: list[string]
- dietary_tags: list[string]
- adventure_level: float
- max_travel_km: float
- company_tags: list[string]
- meal_tags: list[string]
- decision_weights: object<string, float>
- novelty_level: float
- dish_tags: list[string]
- restaurant_affinity_terms: list[string]

### Example object
```json
{
  "cuisine_pref": ["japanese", "thai"],
  "craving_tags": ["spicy", "comfort food"],
  "price_level": {"symbol": "$$", "numeric": 2},
  "vibe_tags": ["cozy / intimate"],
  "dietary_tags": [],
  "adventure_level": 0.75,
  "max_travel_km": 5.0,
  "company_tags": ["small group (3–5)"],
  "meal_tags": ["dinner"],
  "decision_weights": {"ratings": 1.0},
  "novelty_level": 0.5,
  "dish_tags": ["ramen"],
  "restaurant_affinity_terms": ["ippudo", "raku"]
}
```

### Where stored
- profile document field normalized_features

### Which code reads/writes
- build/write: integration/user_profile_model.py -> normalize_answers and integration/user_repo.py -> save_user_profile

---

## 4) profile_text

### Field names and types
- profile_text: string (single concatenated text)

### Example
```json
{
  "profile_text": "top_cuisines: Japanese, Thai | craving_preferences: spicy | ... | novelty preference: mix of both | adventurousness: 4"
}
```

### Where stored
- profile document field profile_text

### Which code reads/writes
- build: integration/user_profile_model.py -> build_profile_text
- write: integration/user_repo.py -> save_user_profile
- read: integration/api.py -> _build_user_embedding_if_available

---

## 5) latest_embedding

### Field names and types
- latest_embedding: object
  - vector: list[float]
  - model_name: string
  - updated_at: datetime/ISO string

### Example
```json
{
  "latest_embedding": {
    "vector": [0.023, -0.051, 0.094],
    "model_name": "multi-qa-MiniLM-L6-cos-v1",
    "updated_at": "2026-04-18T19:05:36.272560"
  }
}
```

### Where stored
- profile document field latest_embedding

### Which code reads/writes
- read: integration/api.py -> _build_user_embedding_if_available
- write: integration/user_repo.py -> update_latest_embedding

---

## 6) Local synthetic user profile format

### Field names and types
- list of objects
  - username: string
  - raw_answers: object (same schema as Raw onboarding answers)

### Example object
```json
{
  "username": "synthetic_spicy_explorer",
  "raw_answers": {
    "top_cuisines": ["Japanese", "Korean", "Thai"],
    "craving_preferences": ["spicy", "fancy/experimental"],
    "price_comfort_level": "$$$",
    "vibes_dining_style": ["lively / buzzy", "date night"],
    "dietary_restrictions": ["None"],
    "adventurousness": 5,
    "travel_willingness": "Anywhere in the city",
    "dining_company": "Partner / couple",
    "typical_meals": ["dinner", "late night"],
    "decision_criteria": ["vibe/atmosphere", "recommendations"],
    "novelty_preference": "try new things",
    "favorite_dishes": ["ramen", "kimchi fried rice", "tom yum"],
    "loved_restaurants": ["Ippudo", "Atoboy"],
    "wishlist_restaurants": ["Atomix", "Jua"],
    "frequent_restaurants": ["Cho Dang Gol", "Soothr", "Raku"],
    "aspirational_restaurants": ["Sushi Noz", "Masa", "Le Bernardin"]
  }
}
```

### Where stored
- data/synthetic_user_profiles.json

### Which code reads/writes
- read: data/pipeline.py -> load_synthetic_user_profiles
- write: static file only (manual edits)

---

## 7) Local DB fallback JSON structure (if present)

### Field names and types
- root object with collection-name keys
- each collection key -> list[document]

### Example structure
```json
{
  "users": [
    {
      "username": "alice",
      "email": "alice@example.com",
      "password": "...",
      "display_name": "Alice",
      "created_at": "2026-04-18T..."
    }
  ],
  "user_profiles": [
    {
      "username": "alice",
      "raw_answers": {"top_cuisines": ["Japanese"]},
      "normalized_features": {"cuisine_pref": ["japanese"]},
      "profile_text": "top_cuisines: Japanese | ...",
      "latest_embedding": {"vector": [0.01], "model_name": "multi-qa-MiniLM-L6-cos-v1", "updated_at": "2026-04-18T..."},
      "updated_at": "2026-04-18T..."
    }
  ],
  "saved_restaurants": [],
  "user_interactions": []
}
```

### Where stored
- data/local_db.json (created lazily)

### Which code reads/writes
- integration/db.py -> _LocalCollection methods find_one/insert_one/update_one/delete_one/find

---

## C. Search personalization flow

Current runtime flow in integration/api.py -> search_restaurants:

1. Load user embedding
- Calls _build_user_embedding_if_available(user_id)
- _build_user_embedding_if_available does:
  - get_user_profile(user_id)
  - if profile.latest_embedding.vector exists -> return it
  - else if profile.profile_text exists -> embed_user(profile_text), persist with update_latest_embedding, return vector
  - else -> return None

2. Determine retrieval mode
- If user_vector_only=True:
  - with user vector -> query_vector = [0]*dim, fused_vector = fuse_vectors(query_vector, user_vector, alpha=1.0)
  - without user vector -> fallback _rank_by_location_and_rating
- If user_vector_only=False:
  - query_vector = embed_query(query)
  - fused_vector = fuse_vectors(query_vector, user_vector, alpha=0.3)
  - if user_vector is None, fuse_vectors returns query_vector unchanged

3. Retrieve and rank
- Candidate retrieval: _retrieve_candidates_cluster_first(fused_vector, ...)
- Filtering: apply_filters + borough filter
- Ranking: rank_candidates(filtered_with_scores, user_history)

4. Where fusion happens
- recommendation/ranker.py -> fuse_vectors

---

## D. MongoDB setup requirements

## 1) Required environment variables
- MONGO_URI (optional now because fallback exists, but required to use real Mongo)
- MONGO_DBNAME (optional; defaults to NearBite)

## 2) Code files that depend on Mongo
- integration/db.py (connection and fallback switch)
- integration/user_repo.py
- integration/interaction_repo.py
- integration/wrapped_repo.py

## 3) If Mongo is available, expected collections/documents
- Collections used by code:
  - users
  - user_profiles
  - saved_restaurants
  - user_interactions
- Documents are created by upsert/insert calls in repository modules.

## 4) If Mongo is NOT available
- integration/db.py sets USE_LOCAL_DB=True
- All repository get_collection calls use local JSON-backed _LocalCollection
- Data persists in data/local_db.json

## 5) What to do locally in your environment
- Create .env with MONGO_URI and optional MONGO_DBNAME if using Mongo.
- If skipping Mongo, leave MONGO_URI unset or invalid and fallback will be used automatically.

## 6) What must be created/configured in MongoDB
- A reachable cluster/database with valid URI credentials.
- No manual collection creation is required (collections are created automatically on first write).

## 7) Is Mongo URI enough?
- Yes, Mongo cluster/database/URI is enough for startup.
- Collections are auto-created by writes.

## 8) Sample .env format
```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority
MONGO_DBNAME=NearBite
```

---

## E. Minimal local setup steps for testing

1) Decide Mongo mode
- Option A: with Mongo -> set MONGO_URI in .env
- Option B: no Mongo -> do nothing for MONGO_URI (local JSON fallback will be used)

2) Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3) Start app
```bash
streamlit run app.py
```

4) Verify onboarding save path
- Log in/sign up
- Open Recommendation page
- Fill onboarding questionnaire and save
- Confirm no errors and profile is marked complete

5) Verify profile document and embedding behavior
- First recommendation/search request for logged-in user should create latest_embedding if absent.
- With Mongo:
  - inspect user_profiles document for raw_answers, normalized_features, profile_text, latest_embedding
- Without Mongo:
  - inspect data/local_db.json for same fields under user_profiles

6) Verify personalization in search
- Discover/search as logged-in user:
  - user_vector_only path should use user embedding if available
- Discover/search as anonymous user:
  - should run without user embedding (query-only or location/rating fallback depending on mode)

7) Optional synthetic data check
- Open data/synthetic_user_profiles.json to confirm available synthetic raw answer payloads.
- If desired, manually insert one synthetic user into user_profiles through a small script using save_user_profile.

---

## Notes on inferred vs explicit behavior
- Explicit in code: profile schema fields, embedding rebuild order, local JSON fallback, fusion alphas (1.0 and 0.3).
- Inferred operational note: “personalization quality” depends on embedding model and profile_text richness; this is not scored explicitly in code.