import logging
from app.agents.state import AgentState
from app.agents.agents import AgentNodes

logger = logging.getLogger(__name__)

# Attempt to load from installed LangGraph library, with a fallback class to guarantee execution
try:
    from langgraph.graph import StateGraph, END
    logger.info("LangGraph package successfully imported.")
except ImportError:
    logger.warning("LangGraph package not found. Activating local Python-native Graph runner simulation...")
    END = "end"
    
    class StateGraph:
        """Fallback simulation class mirroring LangGraph StateGraph API."""
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes = {}
            self.edges = {}
            self.conditional_edges = {}
            self.entry_point = None

        def add_node(self, name: str, func):
            self.nodes[name] = func

        def add_edge(self, source: str, target: str):
            self.edges[source] = target

        def add_conditional_edges(self, source: str, router_func, path_map: dict):
            self.conditional_edges[source] = (router_func, path_map)

        def set_entry_point(self, name: str):
            self.entry_point = name

        def compile(self):
            return CompiledGraph(self)

    class CompiledGraph:
        def __init__(self, graph_definition):
            self.graph = graph_definition

        def invoke(self, initial_state: dict) -> dict:
            """Traverse registered graph nodes and update state variables."""
            state = {
                "messages": initial_state.get("messages", []),
                "user_context": initial_state.get("user_context", {}),
                "current_agent": "None",
                "next_agent": "None",
                "retrieved_context": [],
                "report_content": "",
                "critic_feedback": "",
                "agent_trace": []
            }
            
            current_node = self.graph.entry_point
            max_steps = 25
            step = 0
            
            while current_node and current_node != END and step < max_steps:
                step += 1
                logger.info(f"LangGraph execution: Node '{current_node}' running (Step {step})")
                
                # Execute Node function
                node_func = self.graph.nodes[current_node]
                node_update = node_func(state)
                
                # Apply updates to State dictionary
                for k, v in node_update.items():
                    if k == "messages":
                        state["messages"] = state["messages"] + v
                    elif k == "agent_trace":
                        state["agent_trace"] = state["agent_trace"] + v
                    elif k == "retrieved_context":
                        state["retrieved_context"] = state["retrieved_context"] + v
                    else:
                        state[k] = v
                
                # Decide next edge path
                if current_node in self.graph.conditional_edges:
                    router, paths = self.graph.conditional_edges[current_node]
                    decision = router(state)
                    current_node = paths.get(decision, END)
                elif current_node in self.graph.edges:
                    current_node = self.graph.edges[current_node]
                else:
                    current_node = END
                    
            logger.info("LangGraph execution completed successfully.")
            return state

# ----------------------------------------------------
# BUILD AND COMPILE GRAPH
# ----------------------------------------------------

workflow = StateGraph(AgentState)

# 1. Register Nodes
workflow.add_node("planner", AgentNodes.planner_node)
workflow.add_node("retrieval", AgentNodes.retrieval_node)
workflow.add_node("hr", AgentNodes.hr_node)
workflow.add_node("finance", AgentNodes.finance_node)
workflow.add_node("sales", AgentNodes.sales_node)
workflow.add_node("engineering", AgentNodes.engineering_node)
workflow.add_node("analytics", AgentNodes.analytics_node)
workflow.add_node("document", AgentNodes.document_node)
workflow.add_node("report_generator", AgentNodes.report_generator_node)
workflow.add_node("critic", AgentNodes.critic_node)
workflow.add_node("verification", AgentNodes.verification_node)

# 2. Configure Edges
workflow.set_entry_point("planner")

# Conditional edge from Planner Node
def route_planner(state: AgentState) -> str:
    return state.get("next_agent", "retrieval")

workflow.add_conditional_edges(
    "planner",
    route_planner,
    {
        "retrieval": "retrieval",
        "hr": "hr",
        "finance": "finance",
        "sales": "sales",
        "engineering": "engineering",
        "analytics": "analytics",
        "document": "document"
    }
)

# Standard transitions pointing to Report Generator
for executor_node in ["retrieval", "hr", "finance", "sales", "engineering", "analytics", "document"]:
    workflow.add_edge(executor_node, "report_generator")

workflow.add_edge("report_generator", "critic")

# Conditional edge from Critic Node (rewrites or verifies)
def route_critic(state: AgentState) -> str:
    feedback = state.get("critic_feedback", "")
    return "verify"

workflow.add_conditional_edges(
    "critic",
    route_critic,
    {
        "verify": "verification"
    }
)

# Terminating link
workflow.add_edge("verification", END)

# Compile graph executor
agent_graph = workflow.compile()
