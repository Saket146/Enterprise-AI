from typing import TypedDict, Annotated, List, Dict, Any
from operator import add

class AgentState(TypedDict):
    """
    State tracking schema managed throughout the LangGraph multi-agent execution pipeline.
    """
    # Annotated list allows appending messages to chat history automatically
    messages: Annotated[List[Dict[str, Any]], add]
    
    # Store security contexts of the active user session (id, role, department)
    user_context: Dict[str, Any]
    
    # Track orchestration routing controls
    current_agent: str
    next_agent: str
    
    # Accumulate data chunks retrieved from Postgres, Qdrant and Neo4j
    retrieved_context: List[Dict[str, Any]]
    
    # Temporary workspace for report generation or feedback loops
    report_content: str
    critic_feedback: str
    
    # Store step-by-step latency, token counts and decisions for audit logs
    agent_trace: List[Dict[str, Any]]
