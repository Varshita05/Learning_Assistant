import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


BASE_DIR = Path(__file__).resolve().parents[3]
PROCESSED_DATA = BASE_DIR / "processed_data"


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def extract_chunks(obj, source_file: str) -> list[dict]:
    chunks = []

    if isinstance(obj, list):
        for item in obj:
            chunks.extend(extract_chunks(item, source_file))

    elif isinstance(obj, dict):
        if any(key in obj for key in ("text", "content", "chunk_text")):
            text = (
                obj.get("text")
                or obj.get("content")
                or obj.get("chunk_text")
                or ""
            )

            if isinstance(text, str) and text.strip():
                chunks.append({
                    "content": text,
                    "source": obj.get("source") or obj.get("filename") or source_file,
                    "heading": obj.get("heading"),
                    "page_start": obj.get("page_start"),
                    "page_end": obj.get("page_end"),
                    "parent_id": obj.get("parent_id"),
                })

        for value in obj.values():
            if isinstance(value, (dict, list)):
                chunks.extend(extract_chunks(value, source_file))

    return chunks


def load_chunks() -> list[dict]:
    chunks = []

    for path in PROCESSED_DATA.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            chunks.extend(extract_chunks(data, path.name))
        except Exception:
            continue

    seen = set()
    unique = []

    for chunk in chunks:
        key = (chunk["source"], chunk["content"])

        if key not in seen:
            seen.add(key)
            unique.append(chunk)

    return unique


class BM25Retriever:
    def __init__(self):
        self.rebuild()

    def rebuild(self):
        self.chunks = load_chunks()

        if not self.chunks:
            raise RuntimeError("No chunks found for BM25 index.")

        corpus = [
            tokenize(chunk["content"])
            for chunk in self.chunks
        ]

        self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, limit: int = 8) -> list[dict]:
        scores = self.bm25.get_scores(tokenize(query))

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:limit]

        return [
            {
                **self.chunks[i],
                "bm25_score": float(scores[i]),
            }
            for i in ranked_indices
        ]


bm25_retriever = BM25Retriever()