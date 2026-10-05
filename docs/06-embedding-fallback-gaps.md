# Embedding Providers and Collections

Vector dimensions alone do not define compatibility. Local Sentence Transformers and Gemini embeddings must never share a collection, even if their vectors have the same length.

## Selected Policy

- Local Sentence Transformers is primary.
- Gemini is the fallback provider.
- The active embedder and its collection must be selected together. Never switch embedding models mid-process or query a collection with a different model.
- Keep provider-specific vectors in separate collections. Re-ingest into the matching collection after a provider change; do not wipe production data without a reviewed migration plan.

## Current Implementation Status

The runtime loads the local model first. If local initialization fails, it probes Gemini and selects the `{QDRANT_COLLECTION}_gemini` collection; if neither provider initializes, startup fails. The local model is reported as `fallback` and uses `{QDRANT_COLLECTION}_fallback` for compatibility with existing indexes.

The Gemini model defaults to `gemini-embedding-001` and dimension 768 in configuration. Confirm provider support and collection dimensions before enabling it. `/health` reports the selected model suffix and collection, but does not verify full Qdrant readiness.

## Safe Fallback Behavior

Provider selection should happen at process startup. If local initialization fails, probe Gemini and select its own collection; if both fail, fail startup/readiness rather than silently changing vector spaces during ingestion or retrieval. Verify query/document task types, dimensions, and normalization for each provider with an isolated test collection.