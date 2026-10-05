import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from learning_assistant.config import settings
from learning_assistant.retrieval_services.qdrant_service import (
    search_enterprise_knowledge,
)
from learning_assistant.retrieval_services.ranking_service import (
    rerank_documents,
)


def evaluate_item(item):
    query = item["question"]

    start = time.perf_counter()

    raw_results = search_enterprise_knowledge(
        query,
        limit=settings.RETRIEVE_K,
    )

    retrieval_ms = (time.perf_counter() - start) * 1000

    start = time.perf_counter()

    ranked_results = rerank_documents(
        query,
        raw_results,
        top_n=settings.RERANK_K,
    )

    rerank_ms = (time.perf_counter() - start) * 1000

    return {
        "id": item["id"],
        "question": query,
        "results": ranked_results,
        "retrieval_ms": retrieval_ms,
        "rerank_ms": rerank_ms,
        "gold_evidence": item["gold_evidence"],
    }