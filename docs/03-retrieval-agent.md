# Retrieval + agent

Graph: planner → (retriever \| responder) → responder → END. Memory: `MemorySaver` + `thread_id`.

- Planner: Portkey `complete()`. Output `CONVERSATIONAL` or a search query. History capped to last 4 turns.
- Retriever: Qdrant `RETRIEVE_K=8`, FlashRank `RERANK_K=4`, chunk text capped `MAX_CHUNK_CHARS=600`.
- Responder: Portkey `complete()`, context cap `MAX_CONTEXT_CHARS=6000`, `LLM_MAX_TOKENS=512`.

All LLM traffic except the NeMo gate goes through `gateway/client.py`.
