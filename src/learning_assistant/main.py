
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

import logfire
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))

# Allow `uvicorn main:app` from repo root or src/
import sys

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from learning_assistant.agents.graph import rag_agent
from learning_assistant.auth import (
    Principal,
    authentication_required,
    get_current_principal,
    get_optional_principal,
    require_admin,
    validate_auth_configuration,
)
from learning_assistant.config import settings
from learning_assistant.data_ingestion.processor import run_ingestion
from learning_assistant.guardrails.rails import guard, guard_output, initialize_rails
from learning_assistant.limits import allow, allow_guest_question, cache_get, cache_set
from learning_assistant.retrieval_services.embeddings import get_embedder_name, qdrant_collection
from learning_assistant.study_tools import (
    FLASHCARD_MAX_ITEMS,
    QUIZ_MAX_ITEMS,
    FlashcardItem,
    QuizItem,
    make_flashcards,
    make_quiz,
)

# --------------------- Pydantic Models for Request/Response ---------------------#

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    thread_id: Optional[str] = Field(default="default_user", max_length=128)


class IngestRequest(BaseModel):
    path: str = Field(default=".", min_length=1)
    wipe: bool = Field(default=False)


class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    n: int = Field(default=4, ge=1, le=QUIZ_MAX_ITEMS)


class FlashcardsRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    n: int = Field(default=6, ge=1, le=FLASHCARD_MAX_ITEMS)


class QueryResponse(BaseModel):
    question: str
    answer: str
    status: str
    sources: list
    steps: list[str] = []


class QuizResponse(BaseModel):
    items: list[QuizItem]
    sources: list[dict]
    status: str


class FlashcardsResponse(BaseModel):
    items: list[FlashcardItem]
    sources: list[dict]
    status: str

# --------------------------- FastAPI Application ---------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Initialize application components on startup """
    validate_auth_configuration()
    initialize_rails()
    yield


app = FastAPI(title="Learning_Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------- Utilities -------------------------------- #

def _data_path(p: str) -> str:
    root = Path(settings.INGEST_ROOT).resolve()
    candidate = Path(p)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingestion path must be within the configured corpus root",
        )
    if not resolved.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion path does not exist",
        )
    return str(resolved)


def _cache_key(query: str, thread_id: str) -> str:
    """ Prevents response sharing among different users from same cache entry."""
    normalized_query = "".join(query.lower().split())
    return f"{thread_id}:{normalized_query}"

# ------------------------- API Endpoints ----------------------------- #

@app.get("/")
def home():
    return {"message": "Learning Assistant API is Live",
            "version": "1.0.0"}


@app.get("/health")
def health():
    return {
        "ok": True,
        "embedder": get_embedder_name(),
        "collection": qdrant_collection(),
    }


@app.get("/auth/status")
def auth_status():
    return {"required": authentication_required()}


@app.get("/auth/me")
def auth_me(principal: Principal = Depends(get_current_principal)):
    return {"subject": principal.subject}


@app.get("/graph")
def get_graph_image(principal: Principal = Depends(require_admin)):
    try:
        png = rag_agent.get_graph().draw_mermaid_png()
        return Response(content=png, media_type="image/png")
    except Exception as e:
        logfire.error(f"Graph generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate graph image")

@app.post("/ingest")
def ingest(
    request: IngestRequest,
    principal: Principal = Depends(require_admin),
):
    """Parse → chunk → embed → Qdrant (same pipeline as processor CLI)."""
    path = _data_path(request.path)
    if not os.path.exists(path):
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail=f"Path '{request.path}' does not exist", )
    try:
        run_ingestion(path, wipe_request=request.wipe)
        return {"status": "ok", "path": path, "embedder": get_embedder_name(), "collection": qdrant_collection()}
    except Exception as e:
        logfire.error(f"Ingest failed: {e}")
        raise HTTPException( status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document ingestion failed", )


@app.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    http_request: Request,
    principal: Principal | None = Depends(get_optional_principal),
):
    q = request.query.strip()
    guest_ip = http_request.client.host if http_request.client else "unknown"
    subject = principal.subject if principal else f"guest:{guest_ip}"
    thread_id = f"{subject}:{request.thread_id or 'default_user'}"

    # Rate Limiting
    is_allowed = (
        allow(principal.subject)
        if principal
        else allow_guest_question(guest_ip)
    )
    if not is_allowed:
        return QueryResponse(
            question=q,
            answer="Too many requests. Try again shortly.",
            steps=["rate_limited"],
            status="rate_limited",
            sources=[],
        )

    # Input Guardrails
    fired, rail_msg = guard(q)
    if fired:
        return QueryResponse(
            question=q,
            answer=rail_msg,
            steps=["guardrail"],
            status="guarded",
            sources=[],
        )
    
    cache_key = _cache_key(q, thread_id)
    cached = cache_get(cache_key)
    if cached:
        return {**cached, "status": "cache_hit"}

    initial_state = {
        "messages": [{"role": "user", "content": q}],
        "current_query": q,
        "documents": [],
        "plan": ["Start"],
        "status": "Initializing Graph ....",
    }
    config = {"configurable": {"thread_id": thread_id}}

    # RAG Execution
    try:
        final_output = rag_agent.invoke(initial_state, config=config)
        answer = guard_output(final_output.get("final_answer") or "")
        execution_steps = final_output.get("steps", final_output.get("plan", []))
        payload = {
            "question": q,
            "answer": answer,
            "steps": execution_steps,
            "status": final_output.get("status", "success"),
            "sources": final_output.get("documents", []),
        }
        if payload["status"] != "error":
            cache_set(cache_key, payload)
        return payload
    except Exception as e:
        logfire.error(f"Backend Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error while processing the query",
        )


@app.post("/study/quiz", response_model=QuizResponse)
def study_quiz(
    request: QuizRequest,
    principal: Principal = Depends(get_current_principal),
):
    if not allow(principal.subject):
        raise HTTPException( status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests", )
    try:
        return {**make_quiz(request.topic, request.n), "status": "ok"}
    except Exception as e:
        logfire.error(f"Quiz failed: {e}")
        raise HTTPException( status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Quiz generation failed", )


@app.post("/study/flashcards", response_model=FlashcardsResponse)
def study_flashcards(
    request: FlashcardsRequest,
    principal: Principal = Depends(get_current_principal),
):
    if not allow(principal.subject):
        raise HTTPException( status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests", )
    try:
        return {**make_flashcards(request.topic, request.n), "status": "ok"}
    except Exception as e:
        logfire.error(f"Flashcards failed: {e}")
        raise HTTPException( status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Flashcard generation failed", )
