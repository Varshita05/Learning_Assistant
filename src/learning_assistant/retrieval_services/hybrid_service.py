from learning_assistant.retrieval_services.bm25_service import bm25_retriever
from learning_assistant.retrieval_services.qdrant_service import (
    search_enterprise_knowledge,
)


RRF_K = 60


def document_key(doc: dict):
    return (
        doc.get("source", ""),
        doc.get("page_start"),
        doc.get("page_end"),
        doc.get("heading"),
        doc.get("content", ""),
    )


def hybrid_search(
    query: str,
    limit: int = 5,
    candidate_limit: int = 8,
) -> list[dict]:

    dense_results = search_enterprise_knowledge(
        query,
        limit=candidate_limit,
    )

    bm25_results = bm25_retriever.search(
        query,
        limit=candidate_limit,
    )

    fused = {}

    for rank, doc in enumerate(dense_results, start=1):
        key = document_key(doc)

        fused.setdefault(
            key,
            {"document": doc, "rrf_score": 0.0},
        )

        fused[key]["rrf_score"] += 1.0 / (RRF_K + rank)

    for rank, doc in enumerate(bm25_results, start=1):
        key = document_key(doc)

        fused.setdefault(
            key,
            {"document": doc, "rrf_score": 0.0},
        )

        fused[key]["rrf_score"] += 1.0 / (RRF_K + rank)

    ranked = sorted(
        fused.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    results = []

    for rank, item in enumerate(ranked[:limit], start=1):
        results.append({
            **item["document"],
            "rrf_score": item["rrf_score"],
            # Keeps existing responder UI compatible.
            "rerank_score": item["rrf_score"],
            "retrieval_rank": rank,
        })

    return results