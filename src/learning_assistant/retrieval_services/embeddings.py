import math
import time
import logfire
from learning_assistant.config import settings

BATCH_SIZE = 50
active_model = None
model_type = None  # "gemini" | "fallback"


def _l2(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def probe_gemini():
    """Google embedding-001, truncated+normalized to EMBED_DIM (free-tier friendly)."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        client.models.embed_content(
            model=settings.GEMINI_EMBED_MODEL,
            contents="probe",
            config=types.EmbedContentConfig(
                output_dimensionality=settings.EMBED_DIM,
                task_type="RETRIEVAL_QUERY",
            ),
        )
        logfire.info(
            f"Gemini embeddings ready [{settings.GEMINI_EMBED_MODEL}, {settings.EMBED_DIM}-dim]"
        )
        return client
    except Exception as e:
        logfire.warning(f"Gemini probe failed: {e}. Using local fallback.")
        return None


def load_fallback():
    from sentence_transformers import SentenceTransformer

    logfire.info("loading sentence-transformers fallback (all-mpnet-base-v2)")
    return SentenceTransformer("all-mpnet-base-v2")


def init():
    global active_model, model_type
    if active_model is not None:
        return
    try:
        active_model = load_fallback()
        model_type = "fallback"
    except Exception as local_error:
        active_model = probe_gemini()
        if active_model is None:
            raise RuntimeError("Local and Gemini embedding providers are unavailable") from local_error
        model_type = "gemini"


def get_embedder_name() -> str:
    init()
    return model_type or "fallback"


def qdrant_collection() -> str:
    """One collection per embedder — same dim ≠ same vector space."""
    if model_type == "gemini":
        return f"{settings.QDRANT_COLLECTION}_gemini"

    return f"{settings.QDRANT_COLLECTION}_fallback"


def get_embedding_dim() -> int:
    init()
    if model_type == "gemini":
        return settings.EMBED_DIM
    return active_model.get_sentence_embedding_dimension()


def _gemini_embed(texts: list[str], task: str) -> list[list[float]]:
    from google.genai import types

    last_err = None
    for attempt in range(3):
        try:
            result = active_model.models.embed_content(
                model=settings.GEMINI_EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=settings.EMBED_DIM,
                    task_type=task,
                ),
            )
            if not result.embeddings:
                raise RuntimeError("Gemini returned no embeddings")
            return [_l2(list(e.values)) for e in result.embeddings]
        except Exception as e:
            last_err = e
            err = str(e).lower()
            if not any(x in err for x in ("429", "rate", "quota", "resource_exhausted")):
                raise
            if attempt == 2:
                break
            wait = 2 ** (attempt + 1)
            logfire.warning(f"Gemini embed rate limit — retry {attempt + 1}/3 in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Gemini embed failed: {last_err}")


def embed_batch(batch: list[str]) -> list[list[float]]:
    init()
    if model_type == "fallback":
        return active_model.encode(
            batch, show_progress_bar=False, normalize_embeddings=True
        ).tolist()
    return _gemini_embed(batch, "RETRIEVAL_DOCUMENT")


def embed_query(query: str) -> list[float]:
    init()
    if model_type == "gemini":
        return _gemini_embed([query], "RETRIEVAL_QUERY")[0]
    return active_model.encode([query], normalize_embeddings=True)[0].tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    init()
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        with logfire.span("Embed batch", model=model_type, start=i, size=len(batch)):
            all_embeddings.extend(embed_batch(batch))
    return all_embeddings
