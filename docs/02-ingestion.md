# Ingestion

Pipeline in `src/data_ingestion/processor.py`:

1. Parse: PDF (pypdf + pdfplumber), HTML, txt, docx/pptx (unstructured).
2. Chunk: RecursiveCharacterTextSplitter, size 800 / overlap 120.
3. Local JSON under `processed_data/`.
4. Embed with Gemini-001 (768-d, L2-normalized) or local ST; upsert to `{QDRANT_COLLECTION}_{gemini|fallback}`.

CLI (cwd = `src`):

```
python -m data_ingestion.processor DATA --wipe
```

API: `POST /ingest` `{"path":"DATA","wipe":false}`.

`--wipe` drops the **active** embedder collection only. Re-ingest after Gemini ↔ local switch. See [06-embedding-fallback-gaps.md](06-embedding-fallback-gaps.md).
