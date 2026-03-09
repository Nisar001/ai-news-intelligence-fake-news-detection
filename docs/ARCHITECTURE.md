# Enterprise Architecture Blueprint

## High-Level Architecture
- `FastAPI` async API receives article text/URL and creates analysis jobs.
- `Celery` workers execute heavy NLP, transformer inference, and Gemini summarization.
- `Redis` handles broker, result backend, and hot-cache lookups.
- `PostgreSQL` persists article source, metadata, decisions, summaries, and job telemetry.
- `Nginx` fronts API for reverse proxy and horizontal scale.

## Component Flow
1. Client calls `POST /api/v1/analyze`.
2. API validates input, sanitizes text, stores article, enqueues job.
3. Worker runs NLP pipeline, classifier, explainability, Gemini summary.
4. Worker persists outputs and marks job status.
5. Client polls `GET /api/v1/status/{job_id}` and fetches full result from `GET /api/v1/article/{id}`.

## Data Model
- `articles`: source URL, title, raw/clean text, metadata JSON, timestamp.
- `analysis_jobs`: status, class label, confidence, summaries, risk analysis, keywords, entities, sentiment, explainability payload, processing time, error message.

## API Contracts
### POST `/api/v1/analyze`
Request:
```json
{
  "text": "Long article content ...",
  "include_detailed_summary": false
}
```
Response `202`:
```json
{
  "status": "accepted",
  "job_id": "uuid",
  "article_id": "uuid"
}
```

### POST `/api/v1/summarize`
Request:
```json
{
  "article_id": "uuid",
  "include_detailed_summary": true
}
```
Response `202`: same as analyze.

### GET `/api/v1/status/{job_id}`
Response:
```json
{
  "job_id": "uuid",
  "status": "COMPLETED",
  "classification": "FAKE",
  "confidence": 0.91,
  "processing_ms": 1780,
  "error_message": null
}
```

### GET `/api/v1/article/{id}`
Returns article payload + latest job outputs.

### GET `/api/v1/health`
Returns database and redis readiness.

## NLP Pipeline
- Sanitization and length guards.
- Tokenization, stopword filtering, lemmatization.
- NER extraction via spaCy.
- Sentiment scoring via VADER.
- Keyword extraction and feature vector generation.
- Each stage toggle is config-driven in `configs/app.yaml`.

## Model Strategy
- Transformer classifier loaded from configurable HF checkpoint (`APP_HF_MODEL_NAME`).
- Label confidence and uncertainty thresholds from env/config.
- `REAL` / `FAKE` / `UNCERTAIN` resolved by confidence + margin logic.
- Fine-tuning script in `scripts/train.py`.

## Gemini Prompt Strategy
- Template-based prompt from `configs/prompts.yaml`.
- Strict JSON output contract for parser stability.
- Retry with exponential backoff and timeout.
- Fallback model sequence: primary then fallback.

## Security
- API key validation via `x-api-key`.
- Input sanitization for text and URL.
- CORS restrictions by environment.
- Rate limiting through SlowAPI.
- Secrets only from environment variables.

## Observability
- Structured logs via `structlog`.
- Prometheus metrics exposure.
- Health and status endpoints for orchestration.
- Job processing latency persisted in DB.

## Deployment
1. Set `.env` from `.env.example` including Gemini key.
2. `docker compose up --build`.
3. Run migrations: `alembic upgrade head`.
4. Traffic enters through Nginx to Gunicorn/Uvicorn workers.

## Scaling and Reliability
- Scale API and worker replicas horizontally.
- Redis decouples user-facing API latency from inference latency.
- Postgres with connection pooling and indexed job state queries.
- Retries for Gemini and resilient job state transitions (`FAILED` with error detail).
- Nginx upstream plus stateless API allows rolling deploys.
