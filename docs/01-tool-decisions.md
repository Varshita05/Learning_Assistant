# Tool decisions

| Tool | Decision | Reason |
|---|---|---|
| Qdrant Cloud/local | Keep | Already wired; OSS/free cluster. Collection default `enterprise_rag` (do not rename without `--wipe`). |
| Portkey | Keep as gateway | Free-tier: fallback, simple cache, retries. Virtual-key slugs optional. |
| LiteLLM | Not added | Portkey already present. |
| NeMo Guardrails | Keep thin Colang | Input gate only; output is string checks (no second LLM). |
| Portkey-hosted rails | Not used | Often not on free tier. |
| Embeddings | Primary **Gemini `gemini-embedding-001`** truncated to 768-d; local ST fallback | Free-tier Google embeddings, same Qdrant *size*; **separate collections** so spaces never mix. |
| Groq `llama-3.1-8b-instant` | Primary LLM | Free, OpenAI-compatible via Portkey. Fallback `llama-3.3-70b-versatile`. Replaced `openai/gpt-oss-20b` default. |
| FlashRank | Keep | Local rerank. Fixed singleton + Windows temp cache. |
| In-process cache/RL | Added `limits.py` | No Redis. Complements Portkey. |
| Logfire | Keep | Do not touch credential files. |
| LangGraph 3 nodes | Keep | Enough for study RAG. |
| langchain-openai | Not added | Native Portkey `complete()` instead. |
