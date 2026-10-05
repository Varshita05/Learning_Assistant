import json
import math
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DATASET = BASE_DIR / "evaluation" / "golden_dataset.jsonl"
PROCESSED_DATA = BASE_DIR / "processed_data"

TOP_K = 5
OUTPUT = BASE_DIR / "evaluation" / "bm25_results.json"


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def load_jsonl(path: Path) -> list[dict]:
    items = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                items.append(json.loads(line))

    return items


def extract_chunks(obj, source_file: str) -> list[dict]:
    """
    Recursively find chunk-like dictionaries from processed JSON files.
    """

    chunks = []

    if isinstance(obj, list):
        for item in obj:
            chunks.extend(extract_chunks(item, source_file))

    elif isinstance(obj, dict):

        # Common chunk representation
        if any(
            key in obj
            for key in ("text", "content", "chunk_text")
        ):
            text = (
                obj.get("text")
                or obj.get("content")
                or obj.get("chunk_text")
                or ""
            )

            if isinstance(text, str) and text.strip():
                chunks.append({
                    "text": text,
                    "source": (
                        obj.get("source")
                        or obj.get("filename")
                        or source_file
                    ),
                    "heading": obj.get("heading"),
                    "page_start": obj.get("page_start"),
                    "page_end": obj.get("page_end"),
                    "parent_id": obj.get("parent_id"),
                })

        # Continue searching nested structures
        for value in obj.values():
            if isinstance(value, (dict, list)):
                chunks.extend(
                    extract_chunks(value, source_file)
                )

    return chunks


def load_chunks() -> list[dict]:
    files = list(PROCESSED_DATA.rglob("*.json"))

    if not files:
        raise FileNotFoundError(
            f"No JSON files found under {PROCESSED_DATA}"
        )

    chunks = []

    for path in files:
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )

            chunks.extend(
                extract_chunks(
                    data,
                    path.name
                )
            )

        except Exception as e:
            print(f"Skipping {path}: {e}")

    # Remove exact duplicate chunks
    seen = set()
    unique = []

    for chunk in chunks:
        key = (
            chunk["source"],
            chunk["text"]
        )

        if key not in seen:
            seen.add(key)
            unique.append(chunk)

    return unique


def normalize_source(source: str) -> str:
    source = Path(source).stem.lower()

    source = re.sub(
        r"[^a-z0-9]+",
        " ",
        source
    )

    return source.strip()


def source_matches(
    retrieved_source: str,
    expected_source: str
) -> bool:

    retrieved = normalize_source(
        retrieved_source
    )

    expected = normalize_source(
        expected_source
    )

    # Direct match
    if retrieved == expected:
        return True

    # Expected source may be a shorter logical name
    expected_words = set(expected.split())
    retrieved_words = set(retrieved.split())

    return (
        bool(expected_words)
        and expected_words.issubset(retrieved_words)
    )


def is_relevant(
    chunk: dict,
    expected_sources: list[str]
) -> bool:

    return any(
        source_matches(
            chunk["source"],
            expected
        )
        for expected in expected_sources
    )


# --------------------------------------------------
# METRICS
# --------------------------------------------------

def reciprocal_rank(
    ranked_chunks: list[dict],
    expected_sources: list[str]
) -> float:

    for rank, chunk in enumerate(
        ranked_chunks,
        start=1
    ):
        if is_relevant(chunk, expected_sources):
            return 1.0 / rank

    return 0.0


def recall_at_k(
    ranked_chunks: list[dict],
    expected_sources: list[str],
    k: int
) -> float:

    return float(
        any(
            is_relevant(chunk, expected_sources)
            for chunk in ranked_chunks[:k]
        )
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 60)
    print("BM25 RETRIEVAL EVALUATION")
    print("=" * 60)

    dataset = load_jsonl(DATASET)
    chunks = load_chunks()

    print(f"\nGolden questions : {len(dataset)}")
    print(f"Indexed chunks   : {len(chunks)}")

    if not chunks:
        raise RuntimeError(
            "No chunks could be extracted."
        )

    corpus = [
        tokenize(chunk["text"])
        for chunk in chunks
    ]

    print("Building BM25 index...")

    bm25 = BM25Okapi(corpus)

    results = []

    recall1 = []
    recall3 = []
    recall5 = []
    mrr = []

    for index, item in enumerate(
        dataset,
        start=1
    ):

        question = item["question"]

        expected_sources = (
            item.get("reference_sources")
            or item.get("source")
            or []
        )

        if isinstance(
            expected_sources,
            str
        ):
            expected_sources = [
                expected_sources
            ]

        scores = bm25.get_scores(
            tokenize(question)
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:TOP_K]

        ranked_chunks = [
            {
                **chunks[i],
                "bm25_score": float(scores[i]),
                "rank": rank,
            }
            for rank, i in enumerate(
                ranked_indices,
                start=1
            )
        ]

        r1 = recall_at_k(
            ranked_chunks,
            expected_sources,
            1
        )

        r3 = recall_at_k(
            ranked_chunks,
            expected_sources,
            3
        )

        r5 = recall_at_k(
            ranked_chunks,
            expected_sources,
            5
        )

        rr = reciprocal_rank(
            ranked_chunks,
            expected_sources
        )

        recall1.append(r1)
        recall3.append(r3)
        recall5.append(r5)
        mrr.append(rr)

        results.append({
            "id": item["id"],
            "question": question,
            "expected_sources": expected_sources,
            "retrieved": [
                {
                    "source": c["source"],
                    "heading": c["heading"],
                    "page_start": c["page_start"],
                    "page_end": c["page_end"],
                    "bm25_score": c["bm25_score"],
                    "rank": c["rank"],
                }
                for c in ranked_chunks
            ],
            "recall_at_1": r1,
            "recall_at_3": r3,
            "recall_at_5": r5,
            "reciprocal_rank": rr,
        })

        status = "HIT" if r5 else "MISS"

        print(
            f"[{index}/{len(dataset)}] "
            f"{status:4} | "
            f"R@5={r5:.0f} | "
            f"{question}"
        )

    summary = {
        "questions": len(dataset),
        "chunks": len(chunks),
        "recall_at_1": sum(recall1) / len(recall1),
        "recall_at_3": sum(recall3) / len(recall3),
        "recall_at_5": sum(recall5) / len(recall5),
        "mrr": sum(mrr) / len(mrr),
    }

    output = {
        "method": "BM25",
        "evaluation_type": (
            "document-level source retrieval"
        ),
        "summary": summary,
        "results": results,
    }

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("BM25 RESULTS")
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

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()