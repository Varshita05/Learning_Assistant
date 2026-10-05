import logfire
from learning_assistant.agents.state import AgentState
from learning_assistant.config import settings
from learning_assistant.gateway.client import complete


def _format_context(documents: list[dict]) -> str:
    blocks = []

    for i, doc in enumerate(documents, start=1):
        source = doc.get("source", "Unknown source")
        heading = doc.get("heading") or "Unknown section"
        page_start = doc.get("page_start")
        page_end = doc.get("page_end")

        if page_start and page_end and page_start != page_end:
            pages = f"{page_start}-{page_end}"
        elif page_start:
            pages = str(page_start)
        else:
            pages = "Unknown"

        blocks.append(
            f"""EVIDENCE {i}
SOURCE: {source}
SECTION: {heading}
PAGES: {pages}
RERANK SCORE: {doc.get("rerank_score", 0):.4f}
CONTENT:
{doc.get("content", "")}
"""
        )

    return "\n\n".join(blocks)


def _format_history(messages: list[dict]) -> str:
    history = []

    for msg in messages[:-1][-4:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history.append(f"{role}: {msg['content'][:400]}")

    return "\n".join(history)


def generate_node(state: AgentState):
    query = state["current_query"]
    user_msg = state["messages"][-1]["content"] if state["messages"] else ""

    history_str = _format_history(state["messages"])

    if query == "CONVERSATIONAL":
        prompt = f"""
You are a study assistant.

Answer the latest user message using ONLY the conversation history.

Be concise and natural. Do not invent information.

CONVERSATION HISTORY:
{history_str}

LATEST USER MESSAGE:
{user_msg[:500]}
"""
    else:
        context = _format_context(state["documents"])

        prompt = f"""
You are a study assistant answering questions from indexed study material.

Your task is to answer the user's QUESTION directly and accurately using the
provided EVIDENCE.

RULES:
1. Answer the actual question. Do not simply summarize all evidence.
2. Use only information supported by the evidence.
3. Prioritize evidence that is directly relevant to the question.
4. Do not combine unrelated evidence just because it was retrieved.
5. Explain concepts clearly at a student-friendly level.
6. If useful, give a small example based on the evidence.
7. Do not invent facts, definitions, examples, or details.
8. If the evidence does not contain enough information to answer reliably,
   explicitly say that the indexed material does not provide enough information.
9. When making factual claims from the evidence, cite the source and page
   in this format: [Source, p. X] or [Source, pp. X-Y].
10. Do not mention retrieval, reranking, chunks, embeddings, or internal
    system details.
11. Avoid a generic introduction or conclusion unless it helps answer the
    question.
12. Use a format appropriate to the question:
    - Definition → explanation → example for definition questions.
    - Comparison/table for comparison questions.
    - Ordered steps for process/how-to questions.
    - Focused points for exam-style questions.
    - A concise list/table only when the user asks for an overview.

EVIDENCE:
{context}

CONVERSATION HISTORY:
{history_str}

QUESTION:
{user_msg[:500]}
"""

    with logfire.span("LLM Synthesis"):
        try:
            content = complete(prompt, feature="responder")

            return {
                "final_answer": content,
                "status": "Response generated",
                "plan": state["plan"],
                "messages": [
                    {
                        "role": "assistant",
                        "content": content
                    }
                ],
            }

        except Exception as e:
            logfire.error(f"LLM Generation failed: {e}")

            return {
                "final_answer": "Could not generate an answer right now.",
                "status": "error",
                "plan": state["plan"] + ["LLM error"],
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Could not generate an answer right now."
                    }
                ],
            }