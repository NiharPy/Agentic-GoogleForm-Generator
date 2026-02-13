# app/agents/executor/graph.py
"""
Executor Graph - MCP Version

Updated to use MCP server instead of direct Google API calls
Much simpler and cleaner!
"""

from langgraph.graph import StateGraph, END
from app.agents.executor.state import ExecutorState
from app.agents.executor.nodes.extract_task import extract_task_node
from app.agents.executor.nodes.execute_forms_mcp import execute_forms_mcp_node
from app.agents.executor.nodes.send_response import send_response_node


def build_executor_graph():
    """
    Build the executor agent graph using LangGraph with MCP
    
    Simplified flow (3 nodes instead of 4):
    1. extract_task -> Get task info, form snapshot, user credentials
    2. execute_forms_mcp -> Create form via MCP (replaces 2 nodes!)
    3. send_response -> Send result back to planner
    
    MCP handles:
    - Google API authentication
    - Form/spreadsheet creation
    - Permission management
    - Error handling
    """
    
    builder = StateGraph(ExecutorState)
    
    # Add nodes (only 3 now!)
    builder.add_node("extract_task", extract_task_node)
    builder.add_node("execute_forms_mcp", execute_forms_mcp_node)  # MCP magic happens here
    builder.add_node("send_response", send_response_node)
    
    # Set entry point
    builder.set_entry_point("extract_task")
    
    # Conditional edges with error handling
    
    # After extract_task
    def route_after_extract(state: ExecutorState) -> str:
        if state.get("status") == "failed":
            return "failed"
        return "success"
    
    builder.add_conditional_edges(
        "extract_task",
        route_after_extract,
        {
            "success": "execute_forms_mcp",
            "failed": "send_response"
        }
    )
    
    # After execute_forms_mcp
    builder.add_edge("execute_forms_mcp", "send_response")
    
    # After send_response - end
    builder.add_edge("send_response", END)
    
    return builder.compile()


# Create singleton instance
executor_graph = build_executor_graph()
