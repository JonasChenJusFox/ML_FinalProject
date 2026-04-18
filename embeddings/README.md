# Embeddings Module Guide

This folder has one optional analysis script and two production steps.

## TL;DR: Run Order

Run from repo root.

1. Optional analysis to choose K:
```bash
python -m embeddings.elbow
```

2. Required offline build (creates the files retrieval uses later):
```bash
python -m embeddings.build_index
```

3. Optional smoke test of retrieval from CLI:
```bash
python -m embeddings.cluster_retrieval --query "cozy japanese spot with great service" --k 5
```

## What Each File Is For

- App-critical:
  - `vectorizer.py`: model loading, embedding helpers, cosine similarity.
  - `build_index.py`: offline embedding + clustering, writes retrieval files.
  - `cluster_retrieval.py`: query-time candidate retrieval from those files.
- Investigation only:
  - `elbow.py`: elbow plot for selecting K.
- Convenience:
  - `__init__.py`: re-exports common functions.

## Inputs And Outputs

- Primary input to build:
  - `data/restaurants.json` (list of restaurant dicts)
  - required fields per row: `business_id`, `embedding_text`

- Files created by the build step:
  - `data/restaurant_embeddings.json`
    - shape: `{ "business_id": str, "embedding": list[float], "cluster_id": int }`
  - `data/cluster_centroids.json`
    - shape: `{ "cluster_id": int, "centroid": list[float] }`

- Retrieval output (`cluster_retrieval.py`):
  - `list[tuple[business_id, similarity_score, cluster_id]]`
  - sorted by similarity descending

## Default Parameters And How To Change

### `build_index.py` (CLI)

Defaults:
- `--input data/restaurants.json`
- `--k 20`
- `--embeddings-output data/restaurant_embeddings.json`
- `--centroids-output data/cluster_centroids.json`

Internal defaults (not CLI flags):
- `max_iters=100`
- `seed=42`

Override example:
```bash
python -m embeddings.build_index \
  --input data/restaurants.json \
  --k 25 \
  --embeddings-output data/restaurant_embeddings.json \
  --centroids-output data/cluster_centroids.json
```

### `cluster_retrieval.py` (CLI)

Defaults:
- `--k 20`
- `--index-path data/restaurant_embeddings.json`
- `--centroids-path data/cluster_centroids.json`

Required:
- `--query "..."`

Override examples:
```bash
python -m embeddings.cluster_retrieval --query "sushi omakase sake" --k 5

python -m embeddings.cluster_retrieval \
  --query "spicy ramen near nyu" \
  --index-path data/restaurant_embeddings.json \
  --centroids-path data/cluster_centroids.json
```

### `elbow.py` (analysis only, CLI)

Defaults:
- `--input data/restaurants.json`
- `--k-min 5`
- `--k-max 40`
- `--k-step 5`

Override example:
```bash
python -m embeddings.elbow \
  --input data/restaurants.json \
  --k-min 10 \
  --k-max 40 \
  --k-step 5
```

## How Teammates Should Use This

When the app starts (one time):
```python
index = load_restaurant_index()
centroids = load_centroids()
```

For each user query:
```python
results = retrieve_candidates_from_query(query, index, centroids, k=20)
```

Then match each result to full restaurant details using `business_id` in the ranking/personalization step.

## Common Pitfalls

- Run commands from repo root, or adjust paths.
- If your data, model, or K value changes, rerun `build_index.py` to regenerate the output files.
- Keep the same embedding model for both indexing and query-time retrieval.

