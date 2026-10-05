import os
import tempfile
import time
import logfire
from flashrank import Ranker, RerankRequest

ranker = None


def get_ranker() -> Ranker:
    """Local FlashRank ONNX cross-encoder. Assigns the singleton (was never stored)."""
    global ranker
    if ranker is None:
        logfire.info("Initializing FlashRank model locally ...")
        cache_dir = os.path.join(tempfile.gettempdir(), "flashrank")
        try:
            ranker = Ranker(cache_dir=cache_dir)
        except Exception:
            ranker = Ranker()
    return ranker


def rerank_documents(query: str, documents: list[dict], top_n: int = 5) -> list[dict]:
    """
    Refines retrieval results by re-scoring documents against the query semantically.
    
    Why FlashRank? 
    Standard vector search (Cosine Similarity) is fast but mathematically "fuzzy."
    FlashRank uses a Cross-Encoder approach which is much more precise but usually slow.
    FlashRank solves this by using highly optimized, quantized ONNX models locally.
    """
    if not documents:
        return []

    start_time = time.time()
    logfire.info(f"[Reranker] Sending {len(documents)} docs to FlashRank Cross-Encoder...")

    try:
        ranker = get_ranker()
        
        # FlashRank expects a list of dictionaries with 'id' and 'text'
        passages = [
            {"id": i, "text": doc["content"]}
            for i, doc in enumerate(documents)
        ]

        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)
        
        # Results are returned sorted by highest semantic score first
        reranked_docs = []
        for res in results[:top_n]:
            original = documents[res["id"]]
            reranked_docs.append({
                **original,
                "rerank_score": float(res["score"]),
            })

        duration = time.time() - start_time
        top_score = results[0]['score'] if results else 'N/A'
        logfire.info(f"[Reranker] Done in {duration:.2f}s. Top semantic score: {top_score}")
        
        return reranked_docs

    except Exception as e:
        logfire.error(f"[Reranker] Semantic Reranking Failed: {e}")
        
        # Fallback to the original Qdrant order to ensure the user still gets an answer
        return documents[:top_n]