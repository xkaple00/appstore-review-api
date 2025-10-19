# Apple Store Review Analysis API

REST API that fetches Apple App Store reviews, computes metrics, runs NLP (sentiment + keyword extraction), and returns insights with downloadable raw data and a one-click HTML report.

## Features

- **Data collection** (100 random reviews by default) via one of:
  - `app-store-web-scraper` (scrapes the web App Store; no credentials)
  - Apple RSS JSON feed (best-effort, may be inconsistent)
- **Processing**: text cleaning, fields extraction, safe error handling.
- **Metrics**: average rating, rating distribution.
- **Insights**: Transformers RoBERTa-based sentiment, and actionable recommendations.
- **API** (FastAPI):
  - `POST /collect` — fetch & persist reviews for an app
  - `GET  /metrics` — average rating, rating distribution
  - `GET  /insights` — sentiment + keywords + recommendations
  - `GET  /reviews` — raw reviews (JSON)
  - `GET  /reviews/download` — CSV/JSON download
  - `GET  /report` — HTML report with charts
- **Storage**: lightweight SQLite (via SQLAlchemy) in `reviews.db`.
- **Bonus**: PNG charts embedded in HTML; sample report included.

> Tested on Python 3.10+

## Quickstart

```bash
python -m test_task .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Run API
uvicorn app.main:app --reload --port 8000
```

### Collect 100 reviews for an app

Use *Apple’s numeric app ID* and a 2‑letter country code (e.g., `us`, `gb`, `ua`). You can find the app ID in the store URL, e.g. `https://apps.apple.com/app/id1459969523` → `1459969523`.

```bash
curl -X POST "http://localhost:8000/collect" -H "Content-Type: application/json"   -d '{"app_id": "1459969523", "country": "us", "how_many": 100, "source": "auto"}'
```

### Get metrics & insights
#### For Nebula
```bash
curl "http://localhost:8000/metrics?app_id=1459969523&country=us"
curl "http://localhost:8000/insights?app_id=1459969523&country=us"
curl "http://localhost:8000/reviews?app_id=1459969523&country=us&limit=10000"
curl -OJ "http://localhost:8000/reviews/download?app_id=1459969523&country=us&format=csv"

# HTML report:
curl -OJ 'http://127.0.0.1:8000/report?app_id=1459969523&country=us'

```

#### For TikTok
```bash
curl -X POST "http://localhost:8000/collect" -H "Content-Type: application/json"   -d '{"app_id": "835599320", "country": "us", "how_many": 100, "source": "auto"}'
```

### Get metrics & insights

```bash
curl "http://localhost:8000/metrics?app_id=835599320&country=us"
curl "http://localhost:8000/insights?app_id=835599320&country=us"
curl "http://localhost:8000/reviews?app_id=835599320&country=us&limit=10000"
curl -OJ "http://localhost:8000/reviews/download?app_id=835599320&country=us&format=csv"

# HTML report:
curl -OJ 'http://127.0.0.1:8000/report?app_id=835599320&country=us'

```



## Design Notes

- **Sources**: We default to **RSS JSON** feed. 
- **Sentiment**: Uses Hugging Face `transformers` pipeline.
  - Default model: `cardiffnlp/twitter-roberta-base-sentiment-latest`
  - Multilingual option: `cardiffnlp/twitter-xlm-roberta-base-sentiment`
- **Actionables**: We map negative reviees to friendly recommendations, Qwen/Qwen2.5-1.5B-Instruct used.
- **Random 100**: We fetch a pool (up to a few pages) then sample 100 uniformly to avoid ordering bias.

## Environment

- `REVIEWS_DB_URL` — optional SQLAlchemy URL (default: `sqlite:///./reviews.db`)

## Deploy (Bonus)


```bash
docker build -t appstore-review-api .
docker run -p 8000:8000 appstore-review-api
```

## Video Demo (how-to)

Record a 2–3 min demo with these steps:
1) Start API: `uvicorn app.main:app --reload`
2) POST `/collect` for an app id (e.g., 1459969523).
3) Open `/metrics`, `/insights`, `/report` in the browser.
4) Download `/reviews/download?format=csv`.
5) Narrate how actionables reflect negative reviews.

Use any recorder (OBS, Loom, QuickTime).

---
