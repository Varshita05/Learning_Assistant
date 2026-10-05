# Learning Assistant

A retrieval-augmented study assistant with a FastAPI backend, Qdrant retrieval, a LangGraph answer workflow, and a React/Vite client.

<img width="949" height="500" alt="image" src="https://github.com/user-attachments/assets/ae4001d0-f0d8-43d0-9b59-b77f1c5f6f3f" />

## Current Status

- React/Vite is the sole supported UI. The retired Streamlit client and its dependency have been removed.
- Quiz and flashcard endpoints return validated `items` arrays. The React study screens consume that schema.
- Local Sentence Transformers is primary; Gemini is selected at startup only if local initialization fails. Each provider uses a separate collection.
- Production requires one configured HTTP Basic admin account. Guests can submit one `/query` question per IP address per UTC day; `/study/*`, `/ingest`, and `/graph` require the admin account. Ingestion is confined to `INGEST_ROOT`.
- Local development without credentials uses a local-development identity. Basic credentials are held in browser memory only; production must use HTTPS.
- Conversation state, cache, and rate limits are process-local. The guest daily allowance is not shared across multiple workers or instances; run one API worker or add a shared rate-limit store before scaling horizontally. Behind a reverse proxy, configure Uvicorn to trust forwarded client IPs only from the known proxy addresses. Persistent multi-user history and cloud deployment controls are not implemented yet.

See [docs/00-architecture.md](docs/00-architecture.md), [docs/05-runbook.md](docs/05-runbook.md), and [docs/04-gateway-guardrails-cache.md](docs/04-gateway-guardrails-cache.md).

## Project Layout

- `src/learning_assistant/`: API, agent graph, retrieval, ingestion, gateway, and guardrails.
- `frontend/`: React/Vite application and its tests.
- `evaluation/`: golden datasets, metrics, and evaluation tools.
- `docs/`: architecture, design decisions, operations, and implementation gaps.
- `data/` and `processed_data/`: study materials and processed ingestion artifacts.
- `tests/unit/`: offline backend tests; `tests/integration/`: opt-in service and PDF checks.

## Local Setup

Prerequisites: Python 3.14+, `uv`, Node.js/npm, and a configured Qdrant instance. Copy `.env.example` to `.env` and configure required service values locally; never commit credentials.

```powershell
uv sync
uv run uvicorn learning_assistant.main:app --reload
```

The installed console command is `uv run learning-assistant` (without auto-reload).

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The API defaults to `http://localhost:8000`; the frontend defaults to that URL. Set `VITE_API_URL` in the frontend environment to use another API origin. Open `http://localhost:8000/docs` for the OpenAPI page.

## Checks

```powershell
uv run pytest
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Run integration checks explicitly with `RUN_INTEGRATION_TESTS=1`; see the runbook before using external services.
