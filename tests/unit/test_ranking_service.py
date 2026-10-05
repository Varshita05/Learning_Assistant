import numpy as np

from learning_assistant.retrieval_services import ranking_service


def test_rerank_score_is_native_float(monkeypatch):
    class FakeRanker:
        def rerank(self, request):
            return [{"id": 0, "score": np.float32(0.75)}]

    monkeypatch.setattr(ranking_service, "get_ranker", lambda: FakeRanker())

    results = ranking_service.rerank_documents(
        "query", [{"content": "evidence"}], top_n=1
    )

    assert type(results[0]["rerank_score"]) is float