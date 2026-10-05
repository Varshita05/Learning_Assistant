from learning_assistant.agents.state import AgentState
from learning_assistant.gateway.client import complete
import logfire


def planner_node(state: AgentState):
    """Need retrieval vs conversational. Short prompt; last 4 history turns."""
    prior = state["messages"][:-1][-4:]
    history = ""
    for msg in prior:
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content'][:400]}\n"

    user_message = state["messages"][-1]["content"] if state["messages"] else ""
    prompt = (
        "Study-assistant planner. Output ONLY CONVERSATIONAL or one search query.\n"
        "CONVERSATIONAL = greeting or answerable from history only.\n"
        "Else output a short search query for the study corpus.\n"
        f"HISTORY:\n{history}\nLATEST: {user_message[:500]}"
    )

    with logfire.span("Planner Decision"):
        decision = complete(prompt, feature="planner")
        logfire.info(f"Intent identified: {decision}")

    if decision == "CONVERSATIONAL":
        return {
            "current_query": "CONVERSATIONAL",
            "status": "Handling conversationally (using memory) ...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped"],
        }

    return {
        "current_query": decision,
        "status": f"Searching for: {decision}",
        "plan": ["Intent: Retrieve", f"Search Term: {decision}"],
    }
