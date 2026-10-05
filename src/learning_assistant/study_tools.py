import json
from pydantic import BaseModel, Field, ValidationError
from learning_assistant.config import settings
from learning_assistant.gateway.client import complete
from learning_assistant.retrieval_services.qdrant_service import search_enterprise_knowledge
from learning_assistant.retrieval_services.ranking_service import rerank_documents
from learning_assistant.retrieval_services.quality_filter import is_front_matter

QUIZ_MAX_ITEMS = 6
FLASHCARD_MAX_ITEMS = 8


class QuizItem(BaseModel):
    q: str = Field(min_length=1)
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explain: str = Field(min_length=1)


class FlashcardItem(BaseModel):
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)


def _context(topic: str) -> tuple[str, list]:
    retrieved = search_enterprise_knowledge(topic, limit=8)
    retrieved = [doc for doc in retrieved if not is_front_matter(doc)]
    docs = rerank_documents(topic, retrieved, top_n=4)
    excerpts = []
    for doc in docs:
        location = f"page {doc['page_start']}" if doc.get("page_start") else "page unknown"
        excerpts.append(
            f"SOURCE: {doc.get('source', 'Unknown')} ({location})\n"
            f"HEADING: {doc.get('heading') or 'Unlabeled section'}\n"
            f"{doc.get('content', '')[:1000]}"
        )
    text = "\n\n---\n\n".join(excerpts)[:5000]
    return text, docs


def _json_list(raw: str, item_model: type[BaseModel]) -> list[dict]:
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < 0:
        raise ValueError("Study generation did not return a JSON array")
    try:
        data = json.loads(raw[start : end + 1])
        if not isinstance(data, list):
            raise ValueError("Study generation did not return a JSON array")
        return [item_model.model_validate(item).model_dump() for item in data]
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("Study generation returned invalid items") from exc


def make_quiz(topic: str, n: int = 4) -> dict:
    ctx, docs = _context(topic)
    if not ctx.strip():
        return {"items": [], "sources": []}
    n = max(1, min(n, QUIZ_MAX_ITEMS))
    prompt = (
        f"Write up to {n} multiple-choice questions using only EVIDENCE. "
        "Test useful subject concepts, definitions, processes, or applications. "
        "Every question and its correct answer must be directly supported by an excerpt. "
        "Do not ask about authors, dedications, acknowledgements, prefaces, or document structure. "
        "Do not use outside knowledge or mention a passage the learner cannot see. "
        "Return fewer questions rather than padding weak ones; return [] if no useful evidence exists. "
        "Return a JSON array only: "
        '[{"q":"...","options":["a","b","c","d"],"answer_index":0,"explain":"..."}]\n'
        f"EVIDENCE:\n{ctx}"
    )
    raw = complete(prompt, feature="quiz", max_tokens=settings.STUDY_MAX_TOKENS)
    return {"items": _json_list(raw, QuizItem), "sources": docs}


def make_flashcards(topic: str, n: int = 6) -> dict:
    ctx, docs = _context(topic)
    if not ctx.strip():
        return {"items": [], "sources": []}
    n = max(1, min(n, FLASHCARD_MAX_ITEMS))
    prompt = (
        f"Create up to {n} useful study flashcards using only EVIDENCE. "
        "Each front should ask about a subject concept, definition, process, or application; "
        "each back should give a concise explanation supported by the evidence. "
        "Do not create cards about authors, dedications, acknowledgements, prefaces, or document structure. "
        "Do not use outside knowledge or vague prompts such as 'what does the passage say'. "
        "Return fewer cards rather than padding weak ones; return [] if no useful evidence exists. "
        "Return a JSON array only: "
        '[{"front":"term or prompt","back":"short answer"}]\n'
        f"EVIDENCE:\n{ctx}"
    )
    raw = complete(prompt, feature="flashcards", max_tokens=settings.STUDY_MAX_TOKENS)
    return {"items": _json_list(raw, FlashcardItem), "sources": docs}
