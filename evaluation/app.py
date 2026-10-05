import json
from pathlib import Path

from data_parser import load_dataset, evaluation_questions
from pipeline import evaluate_item
from metrics import recall_at, reciprocal_rank, aggregate

ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "results.json"


def main():
    dataset = evaluation_questions(load_dataset())

    rows = []

    print("=" * 72)
    print("LEARNING ASSISTANT - RETRIEVAL EVALUATION")
    print("=" * 72)
    print(f"Questions: {len(dataset)}")

    for index, item in enumerate(dataset, 1):
        print(
            f"\n[{index}/{len(dataset)}] "
            f"{item['id']}: {item['question']}"
        )

        result = evaluate_item(item)
        gold = item["gold_evidence"][0]

        row = {
            "id": item["id"],
            "question": item["question"],
            "recall@1": recall_at(
                result["results"],
                gold,
                1,
            ),
            "recall@3": recall_at(
                result["results"],
                gold,
                3,
            ),
            "recall@5": recall_at(
                result["results"],
                gold,
                5,
            ),
            "mrr": reciprocal_rank(
                result["results"],
                gold,
            ),
            "retrieval_ms": result["retrieval_ms"],
            "rerank_ms": result["rerank_ms"],
            "top_results": [
                {
                    "source": doc.get("source"),
                    "page_start": doc.get("page_start"),
                    "page_end": doc.get("page_end"),
                    "score": doc.get(
                        "rerank_score",
                        doc.get("score"),
                    ),
                }
                for doc in result["results"][:5]
            ],
        }

        rows.append(row)

        print(
            f"R@1={row['recall@1']:.0%} | "
            f"R@3={row['recall@3']:.0%} | "
            f"R@5={row['recall@5']:.0%} | "
            f"MRR={row['mrr']:.3f} | "
            f"Retrieval={row['retrieval_ms']:.1f}ms | "
            f"Rerank={row['rerank_ms']:.1f}ms"
        )

    summary = aggregate(rows)

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)

    for key, value in summary.items():
        print(f"{key}: {value}")

    OUTPUT_FILE.write_text(
        json.dumps(
            {
                "summary": summary,
                "results": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nDetailed results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()