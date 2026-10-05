import logfire

from learning_assistant.agents.state import AgentState
from learning_assistant.config import settings
from learning_assistant.retrieval_services.hybrid_service import hybrid_search


def retrieve_node(state: AgentState):
    query = state["current_query"]

    with logfire.span("Hybrid Knowledge Retrieval"):
        documents = hybrid_search(
            query,
            limit=settings.RERANK_K,
            candidate_limit=settings.RETRIEVE_K,
        )

        cap = settings.MAX_CHUNK_CHARS

        formatted_docs = [
            {
                **doc,
                "content": doc["content"][:cap],
            }
            for doc in documents
        ]

    return {
        "documents": formatted_docs,
        "status": "Found technical context.",
        "plan": state["plan"] + ["Hybrid Context Retrieved"],
    }