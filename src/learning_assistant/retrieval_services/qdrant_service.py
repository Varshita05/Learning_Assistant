import logfire
from qdrant_client import QdrantClient
from learning_assistant.config import settings
from learning_assistant.retrieval_services.embeddings import embed_query, qdrant_collection, get_embedder_name
from learning_assistant.retrieval_services.quality_filter import is_front_matter


# Initialize Qdrant Client
client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

def search_enterprise_knowledge(query: str, limit: int = 8):
    """
    Performs a high-precision search in the enterprise knowledge base.
    Uses the modern query_points interface.
    """
    try:
        query_vector = embed_query(query)
        collection = qdrant_collection()

        # Using query_points - the modern standard for Qdrant
        response = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit * 2,
            with_payload=True # JSON
        )

        results = []

        for res in response.points:
            payload = res.payload or {}

            results.append({
                "content": payload.get("text", ""),
                "source": payload.get("source", "Unknown"),
                "score": float(res.score),
                "heading": payload.get("heading"),
                "page_start": payload.get("page_start"),
                "page_end": payload.get("page_end"),
                "parent_id": payload.get("parent_id"),
            })

        return [doc for doc in results if not is_front_matter(doc)][:limit]
    except Exception as e:
        logfire.error(f"Qdrant Search Failed: {e}")
        return []