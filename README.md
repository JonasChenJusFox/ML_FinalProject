# NearBite — Current Pipeline and Runtime Guide

This README documents how the project actually works in the current codebase.
It is intentionally explicit so integration behavior is unambiguous.

## What this app is

NearBite is a Streamlit app for NYC restaurant discovery with:
- semantic retrieval for query-driven search,
- structured filtering,
- ranking,
- profile/recommendation pages backed by MongoDB.

Main entrypoint: `app.py`.

## Mandatory setup (before running)

### 1) Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install streamlit-geolocation
```

`streamlit-geolocation` is currently used by Discover but is not listed in `requirements.txt`.

### 2) Configure environment variables

Create `.env` from `env.example` and set:

```bash
MONGO_URI=...
MONGO_DBNAME=NearBite
```

`MONGO_URI` is required at import time by `integration/db.py`; the app can fail to start without it.

### 3) Run app

```bash
streamlit run app.py
```

## Data and artifacts used at runtime

### Required restaurant dataset
- `data/restaurants.json`

### Precomputed embedding artifacts (recommended and currently supported)
- `data/restaurant_embeddings.json`
- `data/cluster_centroids.json`

Cluster-first retrieval uses these files when present.

If you need to regenerate artifacts:

```bash
python -m embeddings.build_index --input data/restaurants.json --k 20
```

First model use may download SentenceTransformer weights.

## Actual page behavior

### Home
- collects search text and navigates to Discover.

### Discover (important)

Discover now calls backend search via `integration.api.search_restaurants(...)`.

Two modes are used intentionally:

1. **Anonymous user (`user_id = "anonymous"`)**
   - query-driven semantic mode (`user_vector_only = False`)
   - flow: query embedding -> retrieval -> filters -> ranking.

2. **Logged-in user**
   - user-vector mode (`user_vector_only = True`)
   - if user vector exists: blank query vector + user vector fusion (`alpha=1.0`)
   - if user vector missing: fallback ranking by location + rating.

### Profile / Recommendation
- use Mongo-backed profile, saved restaurants, wrapped stats, and questionnaire-based recommendation UI.

## Backend search pipeline (current implementation)

Entrypoint: `integration/api.py::search_restaurants`

### Standard semantic mode (`user_vector_only=False`)
1. Build optional user vector (if user interaction data exists).
2. Embed query using `embeddings/vectorizer.py::embed_query`.
3. Fuse query + user vectors (`recommendation/ranker.py::fuse_vectors`, `alpha=0.3`).
4. Retrieve candidates with **cluster-first retrieval**:
   - load `restaurant_embeddings.json` + `cluster_centroids.json`,
   - find nearest clusters,
   - search within selected clusters,
   - fallback to global top-k if cluster artifacts unavailable.
5. Apply structured filters (`recommendation/ranker.py::apply_filters`) plus borough filter.
6. Rank candidates (`recommendation/ranker.py::rank_candidates`).
7. Return top-k (default 20).

### User-vector-only mode (`user_vector_only=True`)
1. Try user vector from user interactions.
2. If available: use zero query vector, fuse with `alpha=1.0`, retrieve/filter/rank.
3. If unavailable: fallback to location+rating ranking (still filtered), return top-k.

## Filter contract

Frontend Discover state uses keys like:
- `discover_categories`
- `discover_prices`
- `discover_min_rating`
- `discover_radius_minutes`
- `discover_borough`

Backend adapts these into ranker schema in `integration/api.py::_adapt_filters`:
- `cuisines`
- `price`
- `min_rating`
- `max_distance_km`
- `borough`

## Key modules (current roles)

- `app.py`: Streamlit app bootstrap.
- `frontend/views/discover.py`: collects Discover inputs and calls backend search.
- `integration/api.py`: backend orchestration and retrieval strategy selection.
- `embeddings/vectorizer.py`: embedding model + cosine + global top-k utilities.
- `embeddings/cluster_retrieval.py`: nearest-cluster + within-cluster candidate retrieval.
- `recommendation/ranker.py`: filtering, fusion, ranking functions.
- `data/pipeline.py`: local restaurant loading and optional local user interactions.

## Known runtime notes

- First semantic request can be slower if model weights are not cached yet.
- Anonymous Discover should now be query-sensitive.
- Logged-in Discover may ignore raw query by design when user-vector-only mode is active.
- Search does not require database-backed user history; it gracefully falls back when unavailable.

## Quick sanity checks

```bash
python -c "from integration.api import search_restaurants; r=search_restaurants('spicy thai noodles', {'discover_min_rating':4.0}, user_id='anonymous', top_k=5); print(len(r), [x.get('name') for x in r[:3]])"
```

If this returns results, backend search path is functioning.

## Testing and Evaluation

This project should be tested around **inferred query intent**, not around users manually selecting filters.
The practical target is:

`user query -> inferred constraints -> candidate retrieval -> ranking -> final results`

### 1) Unit / Component testing

Focus on query understanding and parsed attributes first, since these drive downstream behavior.

Example query:
- `cheap spicy ramen near NYU`

Expected inferred signals:
- price intent: `cheap`
- food/cuisine intent: `ramen`, `spicy`
- location intent: `near NYU`

For debugging, log/print parsed query attributes before retrieval and ranking.
At minimum, print a compact object per query with inferred price, cuisine/food, location, vibe/context, and dietary signals.

Suggested mini test table (can be expanded into test fixtures):

| Query | Expected price intent | Expected food/cuisine intent | Expected location intent | Notes |
|---|---|---|---|---|
| `cheap spicy ramen near NYU` | cheap | ramen, spicy | near NYU | baseline query-understanding check |
| `date night italian in west village` | medium-high (or unspecified) | italian | West Village | should infer vibe/context = date night |
| `vegan quick lunch midtown` | budget-mid (or unspecified) | vegan, lunch | Midtown | should infer dietary + meal context |
| `omakase around soho` | expensive (or unspecified) | omakase/japanese | SoHo | tests cuisine + neighborhood extraction |

### 2) Integration / Pipeline testing

Test full end-to-end behavior through the current backend path in `integration/api.py`.

Core checks for each query:
- explicit query constraints are respected (price/location/cuisine terms in query text)
- semantic intent is preserved (similar meaning still returns relevant places)
- personalization helps ranking but does not overpower explicit query intent

Edge cases to include:
- vague query: `quick lunch`
- specific query: `fried chicken`
- conflicting/impossible query: `cheap omakase under $10 near Times Square`
- location-heavy query: `best thai near columbia university`
- price-heavy query: `best budget sushi under $20`
- user-state split: no-history user vs strong-history user

Practical note:
- because location intent parsing, price intent parsing, and interaction-based recommendation are currently incomplete, these should be priority targets in integration tests and regression checks.

### 3) Qualitative evaluation with sample queries

Use a lightweight manual protocol before tuning weights:

1. Build a benchmark of ~30-50 natural-language queries.
2. For each query, record expected inferred filters/attributes.
3. Run the pipeline and inspect top 5 results.
4. Mark whether inferred constraints were satisfied.
5. Assign a quick relevance score for top-5 results.

Keep this in a simple sheet or markdown table with columns such as:
- query
- expected inferred constraints
- top-5 returned restaurants
- constraint satisfaction (yes/partial/no)
- relevance@5 (manual rating)
- notes/failure mode

Simple metrics to track over time:
- constraint satisfaction rate
- relevance@5
- personalization comparison across synthetic users (for the same query set)

For synthetic-user evaluation, `test_user_profiles.md` already provides extreme profile personas that are useful for checking whether ranking changes are reasonable without breaking explicit query intent.

### 4) Practical debugging checklist

For every test query, log:
- raw query text
- inferred filters / parsed attributes
- retrieved candidate count (before final ranking)
- top ranked results and brief score breakdown (if available)

This makes it easier to spot where intent is lost:
- query parsing issue (wrong inferred constraints)
- retrieval issue (no good candidates)
- ranking issue (good candidates are present but ordered poorly)
