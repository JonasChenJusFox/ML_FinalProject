# NearBite Evaluation Report

## 1. Overview
This report outlines the evaluation pipeline for the NearBite restaurant recommendation system. The pipeline assesses:
- **Parser Accuracy**: How well the NLP query parser extracts structured constraints (price, dietary, cuisine, location).
- **Retrieval/Ranking**: The precision of semantic search and filtering mechanisms.
- **Personalization**: The lift in recommendation relevance when user profiles are applied compared to anonymous queries.
- **Latency**: End-to-end response time per query to ensure UI snappiness.

## 2. Methodology
- **Rule-Based Relevance Definition**: A restaurant is deemed relevant if it matches at least 50% of the explicit constraints defined in the expected ground truth (cuisine, dietary, price). 
- **Synthetic Profiles**: 10 synthetic user scenarios were created representing distinct personas (e.g., vegan, meat-lover, sweet-tooth) to test the `user_id` vector fusion logic.
- **Limitations**: The static JSON dataset size and manual ground truth labeling might not capture full real-world tail query behavior. Furthermore, LLM-based query parsing may be non-deterministic.

## 3. Results Summary
- **Parser Exact Match Accuracy**: 86.41%
- **Average Constraint Match @5**: 96.12%
- **Average Precision @5**: 82.72%
- **Average Personalization Lift @5**: 5.00%
- **Average Latency**: 227.32 ms
- **Total Test Crashes**: 0

## 4. Component Analysis
- **Parser Performance**: Measures the hard constraint extraction. Errors usually stem from implicit intents or complex natural language formulations.
- **Ranking Performance**: Validates that semantic retrieval effectively surfaces relevant matches when blended with hard filters.
- **Personalization Impact**: Demonstrates how user embeddings shift the retrieved candidates towards individual preferences, even for generic queries like "dinner tonight".

## 5. Observations
- **Strengths**: The dual-stage filtering (hard constraints + soft boosts) effectively narrows down candidates while maintaining semantic variety.
- **Weaknesses**: Location parsing can occasionally struggle with sub-neighborhood aliases. Very long conversational queries may dilute the primary search intent vector.

## 6. Next Steps
- **Better Query Parsing**: Transitioning to a structured JSON-mode LLM call or few-shot prompting to increase exact match rates.
- **Improved Ranking Weights**: Fine-tuning the `PROFILE_VECTOR_WEIGHT` and `INTERACTION_VECTOR_WEIGHT` based on deeper interaction logs.
- **Better Location Understanding**: Integrating a proper Geocoding API for exact distance radius calculations instead of borough-level hard filters.