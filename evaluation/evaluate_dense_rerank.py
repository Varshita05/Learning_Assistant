import json
import time
from pathlib import Path

from learning_assistant.config import settings
from learning_assistant.retrieval_services.qdrant_service import (
    search_enterprise_knowledge,
)
from learning_assistant.retrieval_services.ranking_service import (
    rerank_documents,
)


BASE_DIR = Path(__file__).resolve().parents[1]

DATASET = BASE_DIR / "evaluation" / "golden_dataset.jsonl"
OUTPUT = BASE_DIR / "evaluation" / "dense_rerank_results.json"

EVAL_K = 5


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def source_matches(retrieved_source: str, expected_source: str) -> bool:
    retrieved = Path(retrieved_source).stem.lower()
    expected = expected_source.lower()

    retrieved = " ".join(
        retrieved.replace("_", " ").split()
    )
    expected = " ".join(
        expected.replace("_", " ").split()
    )

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


def main():
    print("=" * 65)
    print("DENSE + FLASHRANK RETRIEVAL EVALUATION")
    print("=" * 65)

    dataset = load_jsonl(DATASET)

    print(f"\nQuestions: {len(dataset)}")
    print(f"Retrieval K: {settings.RETRIEVE_K}")
    print(f"Rerank K: {settings.RERANK_K}")

    r1_scores = []
    r3_scores = []
    r5_scores = []
    rr_scores = []

    results = []

    total_start = time.perf_counter()

    for i, item in enumerate(dataset, start=1):
        question = item["question"]
        expected_sources = item.get("source", [])

        if isinstance(expected_sources, str):
            expected_sources = [expected_sources]

        start = time.perf_counter()

        try:
            # Get the same candidate pool used by the RAG pipeline.
            candidates = search_enterprise_knowledge(
                question,
                limit=max(
                    EVAL_K,
                    settings.RETRIEVE_K,
                ),
            )

            # Apply the actual production FlashRank reranker.
            ranked = rerank_documents(
                question,
                candidates,
                top_n=EVAL_K,
            )

            latency = time.perf_counter() - start

            ranked = ranked[:EVAL_K]

            r1 = recall_at_k(
                ranked,
                expected_sources,
                1,
            )

            r3 = recall_at_k(
                ranked,
                expected_sources,
                3,
            )

            r5 = recall_at_k(
                ranked,
                expected_sources,
                5,
            )

            rr = reciprocal_rank(
                ranked,
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
                    doc.get("source", "Unknown")
                    for doc in ranked
                ],
                "retrieved_documents": [
                    {
                        "source": doc.get("source"),
                        "heading": doc.get("heading"),
                        "page_start": doc.get("page_start"),
                        "page_end": doc.get("page_end"),
                        "dense_score": doc.get("score"),
                        "rerank_score": doc.get("rerank_score"),
                    }
                    for doc in ranked
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
                f"[{i}/{len(dataset)}] ERROR | {e}"
            )

    if not results:
        raise RuntimeError("No questions were evaluated.")

    summary = {
        "method": "Dense + FlashRank",
        "questions": len(results),
        "recall_at_1": sum(r1_scores) / len(r1_scores),
        "recall_at_3": sum(r3_scores) / len(r3_scores),
        "recall_at_5": sum(r5_scores) / len(r5_scores),
        "mrr": sum(rr_scores) / len(rr_scores),
        "average_latency_seconds": sum(
            r["latency_seconds"]
            for r in results
        ) / len(results),
        "total_time_seconds":
            time.perf_counter() - total_start,
    }

    output = {
        "summary": summary,
        "results": results,
    }

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("RESULTS")
    print("=" * 65)

    print(f"Recall@1 : {summary['recall_at_1']:.4f}")
    print(f"Recall@3 : {summary['recall_at_3']:.4f}")
    print(f"Recall@5 : {summary['recall_at_5']:.4f}")
    print(f"MRR      : {summary['mrr']:.4f}")
    print(
        f"Avg time : "
        f"{summary['average_latency_seconds']:.2f}s"
    )

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()