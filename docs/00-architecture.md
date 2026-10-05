# Architecture

The service combines a FastAPI API, Qdrant retrieval, a LangGraph answer workflow, and a React/Vite client.

## Request Flows

```text
POST /query
  authenticated admin: per-principal in-process rate limit
  guest: one question per IP per UTC day
  input guardrail
  in-process exact-query cache
  planner -> retriever -> responder
  output guardrail
  cache successful result

POST /study/quiz or /study/flashcards
  retrieve context -> gateway generation -> validate item schema -> return sources

POST /ingest
  load -> chunk -> embed -> upsert to the active Qdrant collection
```

The answer graph is in `src/learning_assistant/agents/`. Study generation is in `study_tools.py`. Quiz responses use `items: [{q, options, answer_index, explain}]`; flashcards use `items: [{front, back}]`. Both include `sources` and `status`. Quiz requests allow 1-6 items; flashcard requests allow 1-8.

## Runtime State

- Local Sentence Transformers is primary. Gemini is selected at startup only if local initialization fails; each provider has a separate collection.
- Collection names include an embedder suffix. Local and Gemini vectors must remain in separate collections and queries must use the matching embedder.
- LangGraph uses in-memory checkpointing. Cache and rate limiting are also process-local; they are not durable or shared across workers.
- Production requires one configured HTTP Basic admin account. `/query` allows anonymous guests one question per IP per UTC day; valid credentials use the admin principal and its per-minute limit. `/study/quiz`, `/study/flashcards`, `/ingest`, and `/graph` require the admin account, and ingestion paths are restricted to `INGEST_ROOT`.
- Local development without credentials uses a local-development identity. The React client holds Basic credentials in memory and clears them on sign-out.
- Rate limits and conversation state are process-local. The guest daily allowance is not shared between API workers or instances, so horizontal deployments require a shared rate-limit store. Behind a reverse proxy, Uvicorn must trust forwarded client IPs only from the known proxy addresses for the per-IP allowance to work correctly.
- Guardrail model traffic currently uses a direct provider client rather than the Portkey gateway; see [04-gateway-guardrails-cache.md](04-gateway-guardrails-cache.md).

React/Vite is the sole supported UI. Backend modules live under `src/learning_assistant/`; evaluation tools and datasets live in `evaluation/`.

For setup and operational commands, see [05-runbook.md](05-runbook.md). Embedding constraints and the selected local-primary/Gemini-fallback policy are in [06-embedding-fallback-gaps.md](06-embedding-fallback-gaps.md).
