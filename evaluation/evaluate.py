import base64
import json
import os
import statistics
import time
from pathlib import Path

import requests
from learning_assistant.gateway.client import complete

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

DATASET = Path(__file__).with_name("golden_dataset.jsonl")
RESULTS = Path(__file__).with_name("golden_results.json")

BATCH_SIZE = 3
QUESTION_GAP_SECONDS = 15
BATCH_GAP_SECONDS = 30

QUERY_TIMEOUT = 120
JUDGE_TIMEOUT = 120


def load_dataset():
    with open(DATASET, "r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def load_existing_results():
    if not RESULTS.exists():
        return []

    try:
        return json.loads(
            RESULTS.read_text(encoding="utf-8")
        )
    except Exception:
        return []


def save_results(results):
    RESULTS.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def get_auth_header():
    username = os.getenv("SINGLE_USER_USERNAME")
    password = os.getenv("SINGLE_USER_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "Set SINGLE_USER_USERNAME and SINGLE_USER_PASSWORD "
            "before running evaluation."
        )

    credentials = f"{username}:{password}".encode("ascii")
    token = base64.b64encode(credentials).decode("ascii")

    return {
        "Authorization": f"Basic {token}"
    }


def run_query(item):
    start = time.perf_counter()

    response = requests.post(
        f"{BASE_URL}/query",
        json={
            "query": item["question"],
            "thread_id": f"evaluation-{item['id']}",
        },
        headers=get_auth_header(),
        timeout=QUERY_TIMEOUT,
    )

    latency = time.perf_counter() - start

    response.raise_for_status()

    data = response.json()

    return {
        "answer": data.get("answer", ""),
        "sources": data.get("sources", []),
        "status": data.get("status"),
        "latency_seconds": latency,
    }


def format_sources(sources):
    if not sources:
        return "No sources were retrieved."

    formatted = []

    for index, source in enumerate(sources, start=1):
        filename = source.get("source", "Unknown")
        heading = source.get("heading", "Unknown")
        page_start = source.get("page_start")
        page_end = source.get("page_end")
        content = source.get("content", "")

        if (
            page_start is not None
            and page_end is not None
            and page_start != page_end
        ):
            pages = f"pp. {page_start}-{page_end}"
        elif page_start is not None:
            pages = f"p. {page_start}"
        else:
            pages = "page unavailable"

        formatted.append(
            f"""SOURCE {index}
FILE: {filename}
SECTION: {heading}
PAGES: {pages}
CONTENT:
{content[:2500]}
"""
        )

    return "\n\n".join(formatted)


def parse_judge_response(text):
    text = text.strip()

    if "```" in text:
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            f"Judge did not return valid JSON: {text[:500]}"
        )

    return json.loads(
        text[start:end + 1]
    )


def judge_answer(item, generated_answer, sources):
    prompt = f"""
You are an evaluation system for a RAG-based study assistant.

Evaluate the generated answer using the question, reference answer,
and retrieved evidence below.

QUESTION:
{item["question"]}

REFERENCE ANSWER:
{item["answer"]}

GENERATED ANSWER:
{generated_answer}

RETRIEVED EVIDENCE:
{format_sources(sources)}

Score each category from 0 to 2.

CORRECTNESS:
0 = incorrect or contradicts the reference/evidence
1 = partially correct
2 = correct

COMPLETENESS:
0 = misses major information
1 = partially covers the required information
2 = covers the important information

FAITHFULNESS:
0 = contains unsupported or invented claims
1 = mostly supported with minor unsupported details
2 = claims are supported by the retrieved evidence

CITATION:
0 = missing or incorrect citations
1 = partially correct citations
2 = citations correctly identify supporting source/page

If the question is unanswerable from the uploaded sources, an answer
that correctly states that the material does not provide enough
information should receive high correctness and faithfulness.

Return ONLY this JSON object.
Do not use Markdown.
Do not add explanations outside the JSON.

{{
  "correctness": 0,
  "completeness": 0,
  "faithfulness": 0,
  "citation": 0,
  "overall": 0,
  "reason": "brief explanation"
}}

The "overall" value must be the average of correctness,
completeness, faithfulness, and citation, rounded to 2 decimal places.
"""

    judge_text = complete(
        prompt,
        feature="evaluation",
    )

    return parse_judge_response(judge_text)


def evaluate_question(item):
    query_result = run_query(item)

    generated_answer = query_result["answer"]
    sources = query_result["sources"]

    # Small delay before the second LLM request.
    time.sleep(QUESTION_GAP_SECONDS)

    judge = judge_answer(
        item,
        generated_answer,
        sources,
    )

    return {
        "id": item["id"],
        "question": item["question"],
        "topic": item.get("topic"),
        "difficulty": item.get("difficulty"),
        "answerable": item.get(
            "answerable_from_uploaded_sources",
            True,
        ),
        "reference_answer": item["answer"],
        "generated_answer": generated_answer,
        "reference_sources": item.get("source", []),
        "retrieved_sources": [
            source.get("source")
            for source in sources
        ],
        "latency_seconds": query_result[
            "latency_seconds"
        ],
        "correctness": judge["correctness"],
        "completeness": judge["completeness"],
        "faithfulness": judge["faithfulness"],
        "citation": judge["citation"],
        "overall": judge["overall"],
        "judge_reason": judge["reason"],
    }


def print_summary(results):
    if not results:
        return

    print()
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    print(f"Questions evaluated : {len(results)}")

    for key in [
        "correctness",
        "completeness",
        "faithfulness",
        "citation",
        "overall",
    ]:
        values = [
            result[key]
            for result in results
            if isinstance(result.get(key), (int, float))
        ]

        if values:
            average = statistics.mean(values)

            print(
                f"{key.capitalize():20}: "
                f"{average:.2f}/2 "
                f"({average / 2:.1%})"
            )

    latencies = [
        result["latency_seconds"]
        for result in results
    ]

    print(
        f"Avg query latency   : "
        f"{statistics.mean(latencies):.2f}s"
    )

    print(
        f"Median query latency: "
        f"{statistics.median(latencies):.2f}s"
    )


def main():
    dataset = load_dataset()

    existing = load_existing_results()

    completed_ids = {
        result["id"]
        for result in existing
    }

    remaining = [
        item
        for item in dataset
        if item["id"] not in completed_ids
    ]

    print("=" * 70)
    print("LEARNING ASSISTANT - LLM GOLDEN DATASET EVALUATION")
    print("=" * 70)
    print(f"Total questions     : {len(dataset)}")
    print(f"Already evaluated   : {len(existing)}")
    print(f"Remaining           : {len(remaining)}")
    print(f"Batch size          : {BATCH_SIZE}")
    print(f"Question gap        : {QUESTION_GAP_SECONDS}s")
    print(f"Batch gap           : {BATCH_GAP_SECONDS}s")
    print()

    results = existing

    for batch_start in range(
        0,
        len(remaining),
        BATCH_SIZE,
    ):
        batch = remaining[
            batch_start:
            batch_start + BATCH_SIZE
        ]

        batch_number = (
            batch_start // BATCH_SIZE
        ) + 1

        total_batches = (
            (len(remaining) + BATCH_SIZE - 1)
            // BATCH_SIZE
        )

        print(
            f"\n{'=' * 70}"
        )
        print(
            f"BATCH {batch_number}/{total_batches}"
        )
        print(
            f"{'=' * 70}"
        )

        for item in batch:
            position = len(results) + 1

            print(
                f"\n[{position}/{len(dataset)}] "
                f"{item['question']}"
            )

            try:
                result = evaluate_question(item)

                results.append(result)

                save_results(results)

                print(
                    f"  Correctness : "
                    f"{result['correctness']}/2"
                )
                print(
                    f"  Completeness: "
                    f"{result['completeness']}/2"
                )
                print(
                    f"  Faithfulness: "
                    f"{result['faithfulness']}/2"
                )
                print(
                    f"  Citation    : "
                    f"{result['citation']}/2"
                )
                print(
                    f"  Overall     : "
                    f"{result['overall']}/2"
                )
                print(
                    f"  Latency     : "
                    f"{result['latency_seconds']:.2f}s"
                )

            except Exception as exc:
                print(
                    f"  ERROR: {exc}"
                )

                # Continue with the next question.
                time.sleep(QUESTION_GAP_SECONDS)

        remaining_after_batch = (
            len(remaining)
            - batch_start
            - len(batch)
        )

        if remaining_after_batch > 0:
            print(
                f"\nBatch complete. "
                f"Waiting {BATCH_GAP_SECONDS}s..."
            )

            time.sleep(BATCH_GAP_SECONDS)

    print_summary(results)

    save_results(results)

    print(
        f"\nDetailed results saved to: "
        f"{RESULTS}"
    )


if __name__ == "__main__":
    main()