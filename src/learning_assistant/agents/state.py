from typing import TypedDict, List, Annotated
import operator

class AgentState(TypedDict):
    # Annotated + operator.add -> for messages to append rather than replace
    
    messages: Annotated[List[dict], operator.add]
    current_query: str
    documents: List[dict]
    plan: List[str]
    status: str
    final_answer: str