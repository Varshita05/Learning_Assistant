# Runbook

## Local Development

Prerequisites: Python 3.14+, `uv`, Node.js/npm, and a configured Qdrant instance. Copy `.env.example` to `.env` and provide the values needed by the services you use. Do not commit `.env`, credential files, or service tokens.

For production, set `APP_ENV=production`, `SINGLE_USER_USERNAME`, `SINGLE_USER_PASSWORD`, `INGEST_ROOT`, and trusted `CORS_ALLOWED_ORIGINS`. Startup fails if credentials are missing. Serve the API and React client over HTTPS; Basic credentials are not safe over plain HTTP. Credentials must be ASCII for HTTP Basic compatibility.

Start the API from the repository root:

```powershell
uv sync
uv run uvicorn learning_assistant.main:app --reload
```

For a normal local launch without auto-reload, use `uv run learning-assistant`.

Start the maintained React client in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The API is at `http://localhost:8000`; OpenAPI is at `/docs`. The client defaults to this API URL. Override it with `VITE_API_URL` when needed.

## API Operations

- `GET /health` reports the selected embedder and collection; it is not a full dependency-readiness check.
- `POST /ingest` accepts a path within `INGEST_ROOT` and a `wipe` flag. It requires the single account. Never use `wipe` on production data.
- `POST /query` accepts `query` and an optional `thread_id`. The thread ID is not authenticated identity.
- `POST /study/quiz` accepts `topic` and `n` from 1 to 6. It returns validated quiz `items`, `sources`, and `status`.
- `POST /study/flashcards` accepts `topic` and `n` from 1 to 8. It returns validated card `items`, `sources`, and `status`.


## Checks

```powershell
uv run pytest
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Run service-dependent checks separately after configuring test services:

```powershell
$env:RUN_INTEGRATION_TESTS = "1"
uv run pytest tests/integration
```

Use only test Qdrant collections and non-production credentials.

## Embedding Collections

The process selects local Sentence Transformers and uses the `_fallback` collection suffix. If local initialization fails, startup probes Gemini and selects the `_gemini` collection. Keep vectors from different embedding models in separate collections and re-ingest into the matching collection after changing models. See [06-embedding-fallback-gaps.md](06-embedding-fallback-gaps.md).
