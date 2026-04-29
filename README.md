# NearBite

NearBite is a Streamlit application for NYC restaurant discovery with semantic retrieval, hard constraints, and personalized ranking.  
This README is an implementation-accurate, deep technical guide to the current pipeline.

## Table of contents

- System overview
- Project structure
- Environment and startup
- End-to-end request lifecycle
- Query parsing and intent extraction
- Filter model (explicit hard vs query hard vs soft preferences)
- Personalization model (profile + interactions)
- Retrieval model (cluster-first with fallback)
- Ranking model and score composition
- Data contracts and schemas
- State and page behavior
- Caching, performance, and failure behavior
- Debugging and validation
- Security and production considerations
- Extension points

## System overview

At a high level, search flow is:

`user query + UI filters + user history -> parse -> vector build -> candidate retrieval -> hard filter -> rank -> display`

Core design principles in the current implementation:

- Keep semantic retrieval always active in Discover.
- Treat user-entered filter controls as strict when explicit.
- Treat parsed intent hints as soft unless they are clearly explicit constraints.
- Preserve query semantics during embedding (minimal cleaning only).
- Degrade gracefully: no Mongo, no cluster artifacts, or no user vector should not break search.

## Project structure

Primary modules involved in runtime search:

- `app.py`: app bootstrap and page configuration.
- `frontend/ui.py`: shell router, global dialogs, and page rendering.
- `frontend/views/discover.py`: query UX, advanced filters, map/cards, backend call.
- `integration/api.py`: orchestration layer for parse/retrieve/filter/rank.
- `embeddings/query_parser.py`: deterministic text signal extraction.
- `embeddings/vectorizer.py`: embedding model and vector utility functions.
- `embeddings/cluster_retrieval.py`: cluster-level candidate retrieval from prebuilt assets.
- `recommendation/ranker.py`: score calculation and weighted preference boosts.
- `data/pipeline.py`: restaurant loading and interaction loading.
- `integration/db.py`: Mongo initialization with local JSON fallback.
- `integration/user_repo.py`: account/profile storage and embedding cache updates.

## Environment and startup

### Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Optional environment variables

```bash
MONGO_URI=...
MONGO_DBNAME=NearBite
```

Behavior:

- If Mongo is reachable, collections are backed by MongoDB.
- If Mongo is unavailable or not configured, app falls back to `data/local_db.json`.

### Run

```bash
streamlit run app.py
```

## End-to-end request lifecycle

Search entrypoint: `integration/api.py::search_restaurants`.

Sequence for Discover (`user_vector_only=False`):

1. Adapt frontend filter payload to canonical backend fields.
2. Parse query text into deterministic intent signals.
3. Build explicit/query hard filter stages and soft preference stage.
4. Build user vector (profile + interactions) when available.
5. Embed the query and fuse query/user vectors.
6. Retrieve candidate restaurants (cluster-first, then global fallback).
7. Add distance/travel metadata from active origin.
8. Apply hard filters.
9. Apply soft fallback when hard filters are too restrictive.
10. Rank candidates using semantic + structured + soft boosts.
11. Return top-k sorted results with scoring metadata.

## Query parsing and intent extraction

Parser: `embeddings/query_parser.py::parse_query`.

Signals extracted:

- Price intent (`cheap`, `moderate`, `expensive`, `luxury`, etc.).
- Dietary terms (`vegan`, `vegetarian`, `halal`, `kosher`, `gluten-free`).
- Cuisine terms (`ramen`, `thai`, `italian`, etc.).
- Occasion/vibe terms (`date_night`, `cozy`, `lively`, etc.).
- Meal context (`lunch`, `dinner`, `late_night`, etc.).
- Location cues:
  - direct labels (`NYU`, boroughs, neighborhoods),
  - zip code,
  - `in <place>` and `near <place>` strict-place detection.
- Distance-time intent (`under 20 minutes`, `within 3 km`, `near me`).

Important detail:

- `minimal_clean_query` intentionally does **not** strip semantic tokens; it only normalizes whitespace.
- This preserves user intent for embedding similarity.

## Filter model

Filter adaptation is handled by `integration/api.py::_adapt_filters`.

### Canonical fields

Adapted filter payload can include:

- `cuisines`
- `price`
- `min_rating`
- `max_distance_km`
- `borough`
- `origin_lat`, `origin_lon`
- `dietary`
- `strict_dietary`
- explicitness booleans (`explicit_cuisines`, `explicit_price`, etc.)

### Three-stage filter strategy

Built by `_build_filter_stages`:

1. `explicit_hard_filters`
   - only constraints explicitly set in UI.
2. `query_hard_filters`
   - starts from explicit filters and adds strict parsed constraints (e.g., hard borough from `in manhattan`).
3. `soft_preferences`
   - parsed hints used as ranking boosts (not immediate exclusions), including cuisine, dietary, location, vibe, meal type, and price hints.

### Why this split exists

The split avoids over-pruning results due to aggressive parser assumptions while still honoring explicit user controls.

## Personalization model

Personalization vectors are built in `integration/api.py`:

- Profile vector: generated from questionnaire-derived `profile_text` via `embed_user`, cached in profile as `latest_embedding`.
- Interaction vector: weighted average of embeddings for interacted businesses.

Interaction weights:

- `save`: `1.0`
- `like`: `1.5`
- `review/love`: `2.0`
- `review/neutral`: `0.5`
- `review/hate`: `0.0`

Blending:

- `PROFILE_VECTOR_WEIGHT = 0.7`
- `INTERACTION_VECTOR_WEIGHT = 0.3`

Final user vector is L2-normalized. Missing components degrade gracefully.

## Retrieval model

Primary retrieval method: cluster-first.

### Cluster-first path

Uses:

- `data/restaurant_embeddings.json`
- `data/cluster_centroids.json`

Flow:

1. Load centroids and indexed embeddings.
2. Compute similarity between fused query vector and centroids.
3. Select nearest clusters.
4. Score items inside selected clusters.
5. Map `business_id` back to full restaurant records.

### Fallback path

If cluster assets are missing or fail to load:

- Build in-memory index from `data/restaurants.json` (or pre-existing embedded vectors).
- Retrieve global top-k via `retrieve_top_k`.

Candidate pool size is widened to roughly `top_k * 3` before filtering to preserve headroom.

## Hard filtering and fallback behavior

After retrieval, candidates are enriched with:

- `distance_km` (Manhattan-style approximation),
- `travel_minutes` (based on 5 km/h walking speed).

Hard filtering sequence:

1. `explicit_hard_filters`
2. `query_hard_filters`
3. Optional strict neighborhood radius clamp for parsed `in/near <neighborhood>` signals.

If output count is too small:

- fallback to explicit-filtered pool,
- then fallback to full candidate pool.

This prevents empty results from over-constrained parsing while preserving strongest constraints first.

## Ranking model and score composition

Ranker: `recommendation/ranker.py::rank_candidates`.

### Base score components

Default normalized component weights:

- `semantic`: `0.60`
- `rating`: `0.10`
- `popularity`: `0.05`
- `price_match`: `0.05`
- `distance`: `0.20`

Component definitions:

- Semantic: cosine similarity from retrieval stage.
- Rating: normalized from 0-5 to 0-1.
- Popularity: bounded log transform of review count.
- Price match: discrete compatibility score between user preference and restaurant price band.
- Distance: proximity score (closer is better).

### Soft preference boosts

Additional weighted boosts are applied for:

- dietary
- location
- cuisine
- price
- vibe
- meal type

Boost weights (separate from base score weights):

- dietary `0.80`
- cuisine `0.40`
- location `0.25`
- price `0.15`
- vibe `0.10`
- meal type `0.10`

Final outputs per restaurant include:

- `semantic_score`
- `final_score`
- `score_breakdown`
- `soft_preference_boost`
- `dietary_match_boost`

## Data contracts and schemas

### Restaurant record (runtime expectation)

Typical fields used across modules:

- `business_id` (string)
- `name` (string)
- `rating` (float)
- `review_count` (int)
- `price` (string like `$`, `$$`, `$$$`)
- `categories` (list[str] or list[dict])
- `latitude`, `longitude` or `coordinates`
- `borough`, `neighborhood`
- `embedding_text` (string used for semantic embedding)
- optional `embedding` (list[float])

### User profile record

Stored in `user_profiles`:

- `username`
- `raw_answers`
- `normalized_features`
- `profile_text`
- `latest_embedding`:
  - `vector`
  - `model_name`
  - `updated_at`

### User interaction record

Expected normalized fields:

- `user_id`
- `business_id`
- `interaction_type` (`save`, `like`, `review`)
- `review_signal` (`love`, `neutral`, `hate`) for review records
- `timestamp`

## State and page behavior

### Discover behavior

`frontend/views/discover.py`:

- always uses `search_restaurants(..., user_vector_only=False)`,
- submits query and filters from session state,
- tracks visible results incrementally,
- resets map focus when result signature changes.

Advanced filter controls are optional; query-first flow remains primary.

### Profile behavior

`frontend/views/profile.py`:

- requires login,
- renders wrapped summary and interaction-linked restaurants,
- exposes questionnaire edit action,
- reads profile/interactions from repo layer.

## Caching, performance, and failure behavior

### Caching

`integration/api.py` keeps module-level caches for:

- full restaurant list,
- global embedding index,
- cluster assets (index + centroids).

### Performance characteristics

- First request can be slower due to model load/download.
- Cluster assets substantially reduce retrieval search scope.
- Candidate oversampling (`top_k * 3`) improves final ranking quality under strict filters.

### Failure behavior (graceful degradation)

- No Mongo: local JSON db fallback.
- No cluster artifacts: global retrieval fallback.
- No user vector: query-only retrieval/ranking still works.
- No interactions/profile: personalization path is skipped without breaking search.

## Debugging and validation

### Fast sanity checks

```bash
python -c "from integration.api import search_restaurants; r=search_restaurants('cheap spicy ramen near nyu', {'discover_borough':'All'}, user_id='anonymous', top_k=5); print(len(r), [x.get('name') for x in r[:3]])"
```

```bash
python -m embeddings.cluster_retrieval --query 'cozy japanese spot' --k 5
```

### Pipeline diagnostics to inspect

When debugging ranking/retrieval regressions, verify:

- parsed query object,
- explicit vs query hard filter payloads,
- candidate count pre-filter and post-filter,
- ranking pool size after fallback,
- top result `score_breakdown`.

## Security and production considerations

Current implementation includes development-oriented shortcuts:

- passwords are stored in plain text in user records,
- no explicit rate limiting,
- no audit trail or role model.

Before production deployment:

- add password hashing (e.g., bcrypt/argon2),
- add auth/session hardening,
- add secure secrets management and TLS validation policies,
- add observability for ranking and retrieval quality metrics.

## Extension points

Common extension patterns:

- Add parser intents in `embeddings/query_parser.py` and map them to `soft_preferences`.
- Add strict filters by extending `_adapt_filters` and `_apply_base_hard_filters`.
- Tune ranking behavior by editing `DEFAULT_RANKING_WEIGHTS` and `BOOST_WEIGHTS`.
- Swap retrieval strategy by extending `_retrieve_candidates_cluster_first`.
- Add A/B comparisons using `debug_compare_queries`.

## Artifact generation reference

Build cluster artifacts:

```bash
python -m embeddings.build_index --input data/restaurants.json --k 20
```

Run optional elbow analysis:

```bash
python -m embeddings.elbow --input data/restaurants.json
```
