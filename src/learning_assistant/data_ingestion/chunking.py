from typing import List, Dict, Any
import re
import logfire

from learning_assistant.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter


CHUNK_SIZE = Settings.CHUNK_SIZE
CHUNK_OVERLAP = Settings.CHUNK_OVERLAP
PARENT_MAX_CHARS = 5000
MAX_PARENT_PAGES = 6


def heading_detection(line: str) -> bool:
    line = line.strip()

    if not line or len(line) > 150:
        return False

    if re.match(r"^\d+(?:\.\d+)*\s+[A-Za-z]", line):
        return True

    if re.match(
        r"^(chapter|appendix|part)\s+"
        r"(?:\d+|[IVXLCDM]+|\w+)\b",
        line,
        re.IGNORECASE,
    ):
        return True

    return False


def build_parent_sections(
    pages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    parents = []
    current_lines = []
    current_pages = []
    current_heading = None

    def flush_current():
        nonlocal current_lines, current_pages, current_heading

        if not current_lines:
            return

        text = "\n".join(current_lines).strip()

        if text:
            parents.append({
                "text": text,
                "heading": current_heading,
                "page_start": min(current_pages),
                "page_end": max(current_pages),
            })

        current_lines = []
        current_pages = []
        current_heading = None

    for page in pages:
        page_number = page["page_number"]
        page_text = page.get("text", "")

        if not page_text.strip():
            continue

        for line in page_text.splitlines():
            line = line.strip()

            if not line:
                continue

            if heading_detection(line):
                flush_current()

                current_heading = line
                current_lines.append(line)
                current_pages.append(page_number)
                continue

            proposed_length = (
                sum(len(x) for x in current_lines)
                + len(current_lines)
                + len(line)
            )

            proposed_page_span = (
                page_number - min(current_pages) + 1
                if current_pages
                else 1
            )

            if current_lines and (
                proposed_length > PARENT_MAX_CHARS
                or proposed_page_span > MAX_PARENT_PAGES
            ):
                flush_current()

            current_lines.append(line)
            current_pages.append(page_number)

    flush_current()

    return parents


def split_parent(parent: Dict[str, Any]) -> List[str]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
            ", ",
            " ",
            "",
        ],
    )

    return [
        chunk.strip()
        for chunk in splitter.split_text(parent["text"])
        if chunk.strip()
    ]


def chunk_text(
    pages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    with logfire.span(
        "Text Chunking",
        page_count=len(pages),
    ):
        if not pages:
            return []

        parents = build_parent_sections(pages)
        children = []

        for parent_index, parent in enumerate(parents):

            parent_id = f"parent_{parent_index}"

            child_texts = split_parent(parent)

            for child_index, child_text in enumerate(child_texts):

                children.append({
                    "child_id": f"{parent_id}_child_{child_index}",
                    "parent_id": parent_id,
                    "text": child_text,
                    "heading": parent["heading"],
                    "page_start": parent["page_start"],
                    "page_end": parent["page_end"],
                    "child_index": child_index,
                    "parent_index": parent_index,
                })

        logfire.info(
            f"Generated {len(children)} child chunks "
            f"from {len(parents)} parent sections"
        )

        return children