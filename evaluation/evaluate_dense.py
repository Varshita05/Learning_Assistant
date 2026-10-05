import json
import time
from pathlib import Path

from learning_assistant.retrieval_services.qdrant_service import (
    search_enterprise_knowledge,
)


BASE_DIR = Path(__file__).resolve().parents[1]

DATASET = BASE_DIR / "evaluation" / "golden_dataset.jsonl"
OUTPUT = BASE_DIR / "evaluation" / "dense_results.json"

TOP_K = 5


def load_jsonl(path: Path) -> list[dict]:
    items = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                items.append(json.loads(line))

    return items


def normalize_source(source: str) -> str:
    source = Path(source).stem.lower()

    replacements = {
        "lecture notes": "nlp lecture notes",
        "nlp lecture notes": "nlp lecture notes",
        "ppt": "nlp ppt",
        "nlp ppt": "nlp ppt",
    }

    source = source.replace("_", " ")
    source = " ".join(source.split())

    return source


def source_matches(
    retrieved_source: str,
    expected_source: str,
) -> bool:

    retrieved = Path(retrieved_source).stem.lower()
    expected = expected_source.lower()

    retrieved = retrieved.replace("_", " ")
    expected = expected.replace("_", " ")

    retrieved = " ".join(retrieved.split())
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


def is_relevant(
    document: dict,
    expected_sources: list[str],
) -> bool:

    source = document.get("source", "")

    return any(
        source_matches(source, expected)
        for expected in expected_sources
    )


def recall_at_k(
    documents: list[dict],
    expected_sources: list[str],
    k: int,
) -> float:

    return float(
        any(
            is_relevant(doc, expected_sources)
            for doc in documents[:k]
        )
    )


def reciprocal_rank(
    documents: list[dict],
    expected_sources: list[str],
) -> float:

    for rank, document in enumerate(
        documents,
        start=1,
    ):
        if is_relevant(
            document,
            expected_sources,
        ):
            return 1.0 / rank

    return 0.0


def main():

    print("=" * 60)
    print("DENSE + FLASHRANK RETRIEVAL EVALUATION")
    print("=" * 60)

    dataset = load_jsonl(DATASET)

    print(f"\nGolden questions: {len(dataset)}")

    recall1 = []
    recall3 = []
    recall5 = []
    mrr = []

    results = []

    total_start = time.perf_counter()

    for index, item in enumerate(
        dataset,
        start=1,
    ):

        question = item["question"]

        expected_sources = (
            item.get("reference_sources")
            or item.get("source")
            or []
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
            documents = search_enterprise_knowledge(
                question,
                limit=TOP_K,
            )

            latency = time.perf_counter() - start

            documents = documents[:TOP_K]

            r1 = recall_at_k(
                documents,
                expected_sources,
                1,
            )

            r3 = recall_at_k(
                documents,
                expected_sources,
                3,
            )

            r5 = recall_at_k(
                documents,
                expected_sources,
                5,
            )

            rr = reciprocal_rank(
                documents,
                expected_sources,
            )

            recall1.append(r1)
            recall3.append(r3)
            recall5.append(r5)
            mrr.append(rr)

            results.append({
                "id": item["id"],
                "question": question,
                "expected_sources": expected_sources,
                "retrieved_sources": [
                    document.get(
                        "source",
                        "Unknown",
                    )
                    for document in documents
                ],
                "retrieved_documents": [
                    {
                        "source": document.get(
                            "source"
                        ),
                        "heading": document.get(
                            "heading"
                        ),
                        "page_start": document.get(
                            "page_start"
                        ),
                        "page_end": document.get(
                            "page_end"
                        ),
                        "score": document.get(
                            "score"
                        ),
                        "rerank_score": document.get(
                            "rerank_score"
                        ),
                    }
                    for document in documents
                ],
                "recall_at_1": r1,
                "recall_at_3": r3,
                "recall_at_5": r5,
                "reciprocal_rank": rr,
                "latency_seconds": latency,
            })

            status = "HIT" if r5 else "MISS"

            print(
                f"[{index}/{len(dataset)}] "
                f"{status:4} | "
                f"R@5={r5:.0f} | "
                f"{latency:.2f}s | "
                f"{question}"
            )

        except Exception as e:

            print(
                f"[{index}/{len(dataset)}] "
                f"ERROR | {e}"
            )

    total_time = time.perf_counter() - total_start

    if not recall1:
        raise RuntimeError(
            "No questions were evaluated."
        )

    summary = {
        "method": "Dense + FlashRank",
        "questions": len(recall1),
        "recall_at_1": sum(recall1) / len(recall1),
        "recall_at_3": sum(recall3) / len(recall3),
        "recall_at_5": sum(recall5) / len(recall5),
        "mrr": sum(mrr) / len(mrr),
        "average_latency_seconds": (
            sum(
                result["latency_seconds"]
                for result in results
            )
            / len(results)
        ),
        "total_time_seconds": total_time,
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

    print("\n" + "=" * 60)
    print("DENSE + FLASHRANK RESULTS")
    print("=" * 60)

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