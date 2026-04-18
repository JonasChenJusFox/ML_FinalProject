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
