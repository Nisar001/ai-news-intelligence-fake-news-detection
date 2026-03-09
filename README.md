# AI News Intelligence & Fake News Detection Platform

Backend platform for article ingestion, credibility analysis, explainable classification, and summarization with asynchronous job processing.

## Overview
The platform accepts article text or URL input, runs an NLP + classification pipeline, generates summaries, and returns structured analysis through versioned REST APIs.

Core capabilities:
- URL or raw-text ingestion
- Fake/Real/Uncertain classification with confidence scoring
- Explainability payload (keywords, entities, sentiment, reasoning)
- Asynchronous processing with job status tracking
- Persistent storage for articles and analysis results

## Technology Stack
- API: FastAPI (async), Pydantic
- Jobs: Celery + Redis
- Database: PostgreSQL + SQLAlchemy async + Alembic migrations
- NLP/ML: Transformers, spaCy, NLTK
- GenAI: Google Gemini API
- Infra: Docker Compose, Nginx, Gunicorn/Uvicorn
- Observability: structured logs, Prometheus instrumentation

## Project Structure
```text
app/
  api/v1/              # versioned API routes
  core/                # config, security, exception handling, logging
  db/                  # models and async session
  repositories/        # DB access layer
  services/            # NLP, scraping, classifier, Gemini, cache
  tasks/               # Celery app and workers
alembic/               # migrations
configs/               # runtime config and prompt templates
nginx/                 # reverse proxy config
postman/               # API collection + environment
scripts/               # model training scripts
streamlit_app.py       # end-to-end UI
run.py                 # local process launcher
```

## API Endpoints
- `POST /api/v1/analyze`
- `POST /api/v1/summarize`
- `GET /api/v1/article/{id}`
- `GET /api/v1/status/{job_id}`
- `GET /api/v1/health`

## Prerequisites
- Python 3.12 (recommended for local backend)
- Redis running on `localhost:6379`
- PostgreSQL running on `localhost:5432`
- Gemini API key with available quota

## Environment Setup
1. Copy the environment template:
```powershell
copy .env.example .env
```
2. Update at minimum:
- `APP_GEMINI_API_KEY`
- `APP_INTERNAL_API_KEYS`
- `APP_DATABASE_URL`
- `APP_REDIS_URL`
- `APP_CELERY_BROKER_URL`
- `APP_CELERY_RESULT_BACKEND`

## Local Run (Single Command)
Install dependencies:
```powershell
pip install -r requirements.txt
```

Apply migrations:
```powershell
alembic upgrade head
```

Start API + worker + Streamlit:
```powershell
python run.py
```

Useful variants:
- API only: `python run.py api --reload`
- Worker only: `python run.py worker`
- UI only: `python run.py streamlit`
- Disable UI in full run: `python run.py all --no-ui`
- Health monitor interval: `python run.py --monitor-interval 5`

## Docker Run
```powershell
docker compose up --build
```
Then run migrations:
```powershell
alembic upgrade head
```

## Streamlit UI
Run:
```powershell
pip install -r requirements-ui.txt
streamlit run streamlit_app.py
```

Default URL:
- `http://localhost:8501`

## Postman
- Collection: `postman/AI-News-Intelligence.postman_collection.json`
- Environment: `postman/AI-News-Local.postman_environment.json`

## Example API Calls
Analyze by URL:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -H "x-api-key: <YOUR_API_KEY>" \
  -d "{\"url\":\"https://example.com/news-article\"}"
```

Check job status:
```bash
curl "http://localhost:8000/api/v1/status/<JOB_ID>" \
  -H "x-api-key: <YOUR_API_KEY>"
```

## Model Training
Training entry point:
- `scripts/train.py`

Example:
```powershell
python scripts/train.py --model-name roberta-base --dataset-name <dataset_name>
```

## Operations Notes
- If job status remains `PENDING`, confirm worker is running and task is registered.
- If summarization fails with `429`, Gemini quota is exhausted; classification still completes with fallback summary handling.
- If `POST /analyze` returns DB table errors, run `alembic upgrade head`.
- If using Python 3.14 locally, some compiled dependencies may fail; use Python 3.12 for local backend.

## Security Notes
- Keep `.env` out of version control.
- Rotate exposed API keys immediately.
- Restrict CORS and API keys for non-development environments.
