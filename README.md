# 🍜 NearBite — Personalized NYC Restaurant Discovery

> Find your next favorite spot — by vibe, not just by stars.

NearBite is a semantic restaurant discovery app for New York City. Unlike traditional apps that rely purely on structured filters (cuisine, price, rating), NearBite lets you search the way you actually think: *"cheap spicy ramen near NYU"* or *"cozy date night spot in the East Village"*. The system combines **semantic search**, **structured filtering**, and **personalized recommendations** based on your dining history.

---

## Team

| Name | Role |
|------|------|
| Yue Li | Data pipeline & preprocessing |
| Fidaa Abdulkareem | Semantic retrieval & embeddings |
| Albee Zhou | Ranking algorithm & personalization |
| Jonas Chen | Frontend (Streamlit UI) |
| Nick Sidoti | Integration, infra & documentation |

---

## Features

- **Semantic Search** — Type natural language queries; the system matches your intent using sentence embeddings
- **Structured Filters** — Narrow by cuisine, price range ($–$$$$$), dietary restrictions, rating, neighborhood, and more
- **Personalized Ranking** — Results ranked by a combination of semantic relevance and your interaction history
- **Content-Based Recommendations** — "More like places you've liked" suggestions
- **Map View** — See results plotted geographically across NYC boroughs

---

## Core Idea

NearBite is an end-to-end ML system: it uses semantic embeddings to retrieve restaurants that match user intent, then applies a ranking model to score and order candidates. The ranking stage combines relevance and business/user features (not just fixed rules). Over time, the system personalizes results using user interaction signals such as clicks and likes.

---

## Repo Structure

```
nearbite/
│
├── app.py                        # Streamlit entry point
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation and setup instructions
├── .env.example                  # Environment variable template
│
├── data/
│   ├── pipeline.py               # Data ingestion, cleaning, user history (Yue)
│   └── __init__.py
│
├── embeddings/
│   ├── vectorizer.py             # Embedding model, query vectorization, cosine similarity (Fidaa)
│   └── __init__.py
│
├── recommendation/
│   ├── ranker.py                 # Feature scoring, weight training, ranking, and personalization (Albee)
│   └── __init__.py
│
├── frontend/
│   ├── ui.py                     # Streamlit UI components and layout (Jonas + Fidaa)
│   └── __init__.py
│
├── integration/
│   ├── api.py                    # Glue layer: orchestrates the full search pipeline (Nick)
│   └── __init__.py
│
├── config/
│   ├── settings.py               # Environment variables and app-wide constants (Nick)
│   └── __init__.py
│
└── tests/
    ├── test_pipeline.py
    ├── test_vectorizer.py
    ├── test_ranker.py
    └── test_api.py
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/JonasChenJusFox/nearbite.git
cd nearbite
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your Yelp API key and database URL
```

### 5. Run the app

```bash
streamlit run app.py
```

---

## Data Sources

| Source | Used For |
|--------|----------|
| [Yelp Fusion API](https://fusion.yelp.com/) | Live restaurant metadata (name, rating, price, categories, hours). Limited to 500 req/day — responses cached locally. |
| [Google Places API](https://developers.google.com/maps/documentation/places/web-service/overview) | Live review text for sentiment analysis, semantic embedding, and vibe matching. |
| [Geocoding API](https://developers.google.com/maps/documentation/geocoding/overview) | Convert latitude and longitude into Google-formatted addresses (reverse geocoding). |
| Synthetic user data | User interaction history for personalization development |

> ⚠️ The Kaggle Yelp NYC dataset (2004–2015) is outdated and should **not** be used as the live recommendation source. It is used only for NLP training and vibe tag extraction.

---

## Algorithm

NearBite uses a custom **Iterative Optimization** engine, not a thin scikit-learn wrapper. We optimize ranking weights by minimizing a loss function over synthetic interaction labels (continuous preference scores) with gradient descent:

$$
w_{new} = w_{old} - \eta \cdot \nabla L
$$

This produces a learned ranking vector that combines semantic relevance, popularity, and price-match signals in a single trainable scoring function.

---

## System Pipeline

### Offline Pipeline

- **Data collection**: ingest restaurant metadata and review text from APIs/datasets
- **Document construction**: build unified restaurant documents (attributes + text signals)
- **Embedding generation**: precompute vector embeddings for restaurant documents
- **Preprocessing / feature prep**: clean fields, normalize categories/locations, and prepare ranking features

### Online Pipeline

- **User query → embedding**: convert the live natural-language query into a vector
- **Semantic retrieval (top-K)**: retrieve the most relevant restaurant candidates by vector similarity
- **Structured filtering**: apply hard constraints (price, cuisine, dietary, neighborhood, etc.)
- **Model-based ranking (learnable)**: score candidates with a learnable ranking component
- **Return results**: serve ranked cards + map-ready outputs to the UI
- **Log interactions**: store clicks/likes/conversions for future personalization updates

---

## Ranking and Personalization

- **Ranking as a prediction problem**: each candidate is scored by a learned model rather than fixed manual constants
- **Learned feature vector**: core features include semantic similarity, popularity (rating/review signals), and price match
- **Interaction-driven updates**: user feedback (clicks, likes) provides supervision to iteratively refine model weights via gradient-based optimization
- **Cold-start strategy**: new users begin with a **Global Prior** model; as feedback accumulates, the system transitions to a **Personalized Model**
- **User profile modeling**: interaction history is aggregated into a user profile (cuisine, dietary, price, location preferences) that informs feature computation and personalization

---

## Tech Stack

- **Frontend**: Streamlit
- **Backend / API**: Python (Flask integration layer planned)
- **Database**: PostgreSQL + pgvector extension
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **Hosting**: DigitalOcean
- **Design**: Figma ([view mockup](https://www.figma.com/design/zUGZE1xR7Cmf2L2Rhprhge/NearBiteWithIcon))

---

## Running Tests

```bash
pytest tests/
```

---

## Task Board

[GitHub Project Board](https://github.com/users/JonasChenJusFox/projects/2/views/1)
