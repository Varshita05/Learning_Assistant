import os
from pathlib import Path
from collections import Counter

import pytest

from learning_assistant.data_ingestion.loader import parse_pdf
from learning_assistant.data_ingestion.chunking import (
    chunk_text,
    CHUNK_SIZE
)

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "data"
PDF_FILES = sorted(
    path for path in PDF_DIR.rglob("*") if path.suffix.lower() == ".pdf"
)


def validate_pdf(file_path: Path):
    print("\n" + "=" * 70)
    print(f"PDF: {file_path.name}")
    print("=" * 70)

    pages = parse_pdf(str(file_path))
    chunks = chunk_text(pages)

    assert pages, "No pages extracted"
    assert chunks, "No chunks generated"

    # 1. Basic coverage
    print(f"Pages extracted : {len(pages)}")
    print(f"Child chunks    : {len(chunks)}")

    # 2. Empty chunks
    empty_chunks = [
        c for c in chunks
        if not c["text"].strip()
    ]

    # 3. Chunk size distribution
    lengths = [len(c["text"]) for c in chunks]

    below_half = sum(
        length < CHUNK_SIZE * 0.5
        for length in lengths
    )

    oversized = sum(
        length > CHUNK_SIZE * 1.2
        for length in lengths
    )

    print(f"Empty chunks    : {len(empty_chunks)}")
    print(f"Avg chunk size  : {sum(lengths) / len(lengths):.0f}")
    print(f"Min chunk size  : {min(lengths)}")
    print(f"Max chunk size  : {max(lengths)}")
    print(f"< 50% size      : {below_half}")
    print(f"> 120% size     : {oversized}")

    # 4. Duplicate chunks
    counts = Counter(c["text"] for c in chunks)
    duplicate_groups = sum(
        1 for count in counts.values()
        if count > 1
    )

    duplicate_chunks = sum(
        count for count in counts.values()
        if count > 1
    )

    print(f"Duplicate groups: {duplicate_groups}")
    print(f"Duplicate chunks : {duplicate_chunks}")

    # 5. Parent-child integrity
    parent_ids = {
        c["parent_id"]
        for c in chunks
    }

    invalid_parent_ids = [
        c for c in chunks
        if c["parent_id"] not in parent_ids
    ]

    missing_metadata = [
        c for c in chunks
        if (
            not c.get("heading")
            and c.get("page_start") is None
        )
    ]

    print(f"Parent sections : {len(parent_ids)}")
    print(f"Metadata issues  : {len(missing_metadata)}")

    # 6. Children per parent
    children_per_parent = Counter(
        c["parent_id"]
        for c in chunks
    )

    multi_child_parents = sum(
        count > 1
        for count in children_per_parent.values()
    )

    print(f"Parents with >1 child: {multi_child_parents}")

    # 7. Assertions
    assert len(empty_chunks) == 0
    assert len(missing_metadata) == 0
    assert not invalid_parent_ids
    assert duplicate_chunks / len(chunks) < 0.10

    # 8. Sample chunks
    print("\nSample chunks:")
    for chunk in chunks[:3]:
        print("-" * 50)
        print(
            f"Parent: {chunk['parent_id']} | "
            f"Pages: {chunk['page_start']}-{chunk['page_end']}"
        )
        print(chunk["text"][:500].replace("\n", " "))


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run PDF ingestion checks",
)
@pytest.mark.skipif(not PDF_FILES, reason="No sample PDFs found under data/")
def test_final_chunk_quality():
    for pdf_file in PDF_FILES:
        assert pdf_file.exists(), f"Missing file: {pdf_file}"
        validate_pdf(pdf_file)