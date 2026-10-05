from data_parser import gold_match


def recall_at(results, gold, k):
    return float(
        any(gold_match(doc, gold) for doc in results[:k])
    )


def reciprocal_rank(results, gold):
    for rank, doc in enumerate(results, 1):
        if gold_match(doc, gold):
            return 1.0 / rank

    return 0.0


def aggregate(rows):
    n = len(rows) or 1

    return {
        "questions_evaluated": len(rows),
        "recall@1": round(
            sum(row["recall@1"] for row in rows) / n, 4
        ),
        "recall@3": round(
            sum(row["recall@3"] for row in rows) / n, 4
        ),
        "recall@5": round(
            sum(row["recall@5"] for row in rows) / n, 4
        ),
        "mrr": round(
            sum(row["mrr"] for row in rows) / n, 4
        ),
        "avg_retrieval_ms": round(
            sum(row["retrieval_ms"] for row in rows) / n, 2
        ),
        "avg_rerank_ms": round(
            sum(row["rerank_ms"] for row in rows) / n, 2
        ),
    }