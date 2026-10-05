import os

import pytest

from learning_assistant.retrieval_services.qdrant_service import search_enterprise_knowledge


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to query Qdrant",
)
def test_retrieval_returns_results_from_qdrant():
    results = search_enterprise_knowledge(
        "What is natural language processing?", limit=8
    )

    assert isinstance(results, list)