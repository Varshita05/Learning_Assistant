import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_dataset(path=None):
    path = Path(path or ROOT / "golden_dataset.json")
    return json.loads(path.read_text(encoding="utf-8"))


def evaluation_questions(dataset):
    return [
        item
        for item in dataset
        if item.get("include_in_retrieval_eval")
    ]


def gold_match(doc, gold):
    if not gold:
        return False

    source_ok = (
        Path(str(doc.get("source", ""))).name.lower()
        == Path(gold["source"]).name.lower()
    )

    if not source_ok:
        return False

    page_start = doc.get("page_start")
    page_end = doc.get("page_end")

    if page_start is None or page_end is None:
        return False

    return (
        int(page_start) <= gold["page_end"]
        and int(page_end) >= gold["page_start"]
    )