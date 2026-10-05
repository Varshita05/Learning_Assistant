import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_ENV = os.getenv("APP_ENV", "development").lower()
    SINGLE_USER_USERNAME = os.getenv("SINGLE_USER_USERNAME", "")
    SINGLE_USER_PASSWORD = os.getenv("SINGLE_USER_PASSWORD", "")
    INGEST_ROOT = os.getenv(
        "INGEST_ROOT", str(Path(__file__).resolve().parents[2] / "data")
    )
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
        ).split(",")
        if origin.strip()
    ]

    # LLM (Groq free tier). Do not put secrets in this file.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")

    # Portkey gateway (virtual-key slugs optional; see docs/04)
    PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
    GROQ_SLUG = os.getenv("PORTKEY_GROQ_SLUG", "")
    GROQ_SLUG_1 = os.getenv("PORTKEY_GROQ_SLUG_FALLBACK", "")

    # Qdrant
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_URL = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "enterprise_rag")
    GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

    CHUNK_SIZE = 600
    CHUNK_OVERLAP = 80
    
    RETRIEVE_K = 10
    RERANK_K = 5
    
    MAX_CHUNK_CHARS = 1200
    MAX_CONTEXT_CHARS = 8000
    
    LLM_MAX_TOKENS = 768
    STUDY_MAX_TOKENS = 1000
    
    CACHE_TTL_SECONDS = 600
    RATE_LIMIT_PER_MINUTE = 20

    PORTKEY_CONFIG = os.getenv("PORTKEY_CONFIG")


settings = Settings()
