import json
import math
import time
from pathlib import Path

from rank_bm25 import BM25Okapi

from learning_assistant.retrieval_services.qdrant_service import (
    search_enterprise_knowledge,
)


BASE_DIR = Path(__file__).resolve().parents[1]

DATASET = BASE_DIR / "evaluation" / "golden_dataset.jsonl"
PROCESSED_DATA = BASE_DIR / "processed_data"

TOP_K = 5
CANDIDATE_K = 8
RRF_K = 60


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def normalize_source(source: str) -> str:
    source = Path(source).stem.lower()
    source = source.replace("_", " ")
    return " ".join(source.split())


def source_matches(retrieved_source: str, expected_source: str) -> bool:
    retrieved = normalize_source(retrieved_source)
    expected = expected_source.lower().replace("_", " ")
    expected = " ".join(expected.split())

    aliases = {
        "nlp lecture notes":
            "natural language processing lecture notes",
        "nlp ppt":
            "natural language processing ppt",
        "foundations of statistical nlp":
            "foundations of statistical natural language processing",
        "speech and language processing":
            "speech and language processing",
    }

    expected = aliases.get(expected, expected)

    return (
        retrieved == expected
        or expected in retrieved
        or retrieved in expected
    )


def relevant(doc, expected_sources):
    return any(
        source_matches(
            doc.get("source", ""),
            expected,
        )
        for expected in expected_sources
    )


def recall_at_k(docs, expected_sources, k):
    return float(
        any(
            relevant(doc, expected_sources)
            for doc in docs[:k]
        )
    )


def reciprocal_rank(docs, expected_sources):
    for rank, doc in enumerate(docs, start=1):
        if relevant(doc, expected_sources):
            return 1.0 / rank

    return 0.0


def tokenize(text):
    return text.lower().split()


def load_bm25_documents():
    documents = []

    for path in PROCESSED_DATA.rglob("*.json"):
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            continue

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("chunks")
                or data.get("documents")
                or data.get("data")
                or []
            )
        else:
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            text = (
                item.get("text")
                or item.get("content")
                or ""
            )

            if not text.strip():
                continue

            documents.append({
                "content": text,
                "source": item.get(
                    "source",
                    path.stem,
                ),
                "heading": item.get("heading"),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
            })

    return documents


def build_bm25():
    documents = load_bm25_documents()

    corpus = [
        tokenize(doc["content"])
        for doc in documents
    ]

    return (
        documents,
        BM25Okapi(corpus),
    )


def bm25_search(
    query,
    documents,
    bm25,
    limit=CANDIDATE_K,
):
    scores = bm25.get_scores(
        tokenize(query)
    )

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:limit]

    results = []

    for index in ranked_indices:
        doc = dict(documents[index])
        doc["bm25_score"] = float(
            scores[index]
        )
        results.append(doc)

    return results


def document_key(doc):
    return (
        doc.get("source", ""),
        doc.get("page_start"),
        doc.get("page_end"),
        doc.get("heading"),
        doc.get("content", ""),
    )


def rrf_fusion(dense_docs, bm25_docs):
    fused = {}

    # Dense ranking contribution
    for rank, doc in enumerate(
        dense_docs,
        start=1,
    ):
        key = document_key(doc)

        fused.setdefault(
            key,
            {
                "document": doc,
                "rrf_score": 0.0,
            },
        )

        fused[key]["rrf_score"] += (
            1.0 / (RRF_K + rank)
        )

    # BM25 ranking contribution
    for rank, doc in enumerate(
        bm25_docs,
        start=1,
    ):
        key = document_key(doc)

        fused.setdefault(
            key,
            {
                "document": doc,
                "rrf_score": 0.0,
            },
        )

        fused[key]["rrf_score"] += (
            1.0 / (RRF_K + rank)
        )

    ranked = sorted(
        fused.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    results = []

    for item in ranked[:TOP_K]:
        doc = dict(item["document"])
        doc["rrf_score"] = item["rrf_score"]
        results.append(doc)

    return results


def main():
    print("=" * 65)
    print("HYBRID BM25 + DENSE RETRIEVAL EVALUATION")
    print("=" * 65)

    dataset = load_jsonl(DATASET)

    print(f"\nQuestions: {len(dataset)}")

    print("Building BM25 index...")
    bm25_documents, bm25 = build_bm25()

    print(
        f"BM25 documents: "
        f"{len(bm25_documents)}"
    )

    r1_scores = []
    r3_scores = []
    r5_scores = []
    rr_scores = []

    results = []

    total_start = time.perf_counter()

    for i, item in enumerate(
        dataset,
        start=1,
    ):
        question = item["question"]

        expected_sources = item.get(
            "source",
            [],
        )

        if isinstance(
            expected_sources,
            str,
        ):
            expected_sources = [
                expected_sources
            ]

        start = time.perf_counter()

        try:
            # Dense candidate retrieval
            dense_docs = (
                search_enterprise_knowledge(
                    question,
                    limit=CANDIDATE_K,
                )
            )

            # BM25 candidate retrieval
            bm25_docs = bm25_search(
                question,
                bm25_documents,
                bm25,
                limit=CANDIDATE_K,
            )

            # Reciprocal Rank Fusion
            hybrid_docs = rrf_fusion(
                dense_docs,
                bm25_docs,
            )

            latency = (
                time.perf_counter() - start
            )

            r1 = recall_at_k(
                hybrid_docs,
                expected_sources,
                1,
            )

            r3 = recall_at_k(
                hybrid_docs,
                expected_sources,
                3,
            )

            r5 = recall_at_k(
                hybrid_docs,
                expected_sources,
                5,
            )

            rr = reciprocal_rank(
                hybrid_docs,
                expected_sources,
            )

            r1_scores.append(r1)
            r3_scores.append(r3)
            r5_scores.append(r5)
            rr_scores.append(rr)

            results.append({
                "id": item["id"],
                "question": question,
                "expected_sources": expected_sources,
                "retrieved_sources": [
                    doc.get(
                        "source",
                        "Unknown",
                    )
                    for doc in hybrid_docs
                ],
                "retrieved_documents": [
                    {
                        "source": doc.get(
                            "source"
                        ),
                        "heading": doc.get(
                            "heading"
                        ),
                        "page_start": doc.get(
                            "page_start"
                        ),
                        "page_end": doc.get(
                            "page_end"
                        ),
                        "rrf_score": doc.get(
                            "rrf_score"
                        ),
                    }
                    for doc in hybrid_docs
                ],
                "recall_at_1": r1,
                "recall_at_3": r3,
                "recall_at_5": r5,
                "reciprocal_rank": rr,
                "latency_seconds": latency,
            })

            print(
                f"[{i}/{len(dataset)}] "
                f"{'HIT' if r5 else 'MISS':4} | "
                f"R@5={r5:.0f} | "
                f"{latency:.2f}s | "
                f"{question}"
            )

        except Exception as e:
            print(
                f"[{i}/{len(dataset)}] "
                f"ERROR | {e}"
            )

    if not results:
        raise RuntimeError(
            "No questions were evaluated."
        )

    summary = {
        "method": "Hybrid BM25 + Dense RRF",
        "questions": len(results),
        "recall_at_1": (
            sum(r1_scores) /
            len(r1_scores)
        ),
        "recall_at_3": (
            sum(r3_scores) /
            len(r3_scores)
        ),
        "recall_at_5": (
            sum(r5_scores) /
            len(r5_scores)
        ),
        "mrr": (
            sum(rr_scores) /
            len(rr_scores)
        ),
        "average_latency_seconds": (
            sum(
                r["latency_seconds"]
                for r in results
            ) / len(results)
        ),
        "total_time_seconds": (
            time.perf_counter() -
            total_start
        ),
    }

    output = {
        "summary": summary,
        "results": results,
    }

    OUTPUT = (
        BASE_DIR /
        "evaluation" /
        "hybrid_results.json"
    )

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("HYBRID RESULTS")
    print("=" * 65)

    print(
        f"Recall@1 : "
        f"{summary['recall_at_1']:.4f}"
    )

    print(
        f"Recall@3 : "
        f"{summary['recall_at_3']:.4f}"
    )

    print(
        f"Recall@5 : "
        f"{summary['recall_at_5']:.4f}"
    )

    print(
        f"MRR      : "
        f"{summary['mrr']:.4f}"
    )

    print(
        f"Avg time : "
        f"{summary['average_latency_seconds']:.2f}s"
    )

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()