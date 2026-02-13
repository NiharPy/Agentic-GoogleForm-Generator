from langgraph.graph import StateGraph, END
from app.agents.planner.state import PlannerState
from app.agents.executor.nodes.validator import validator_node

def build_executor_graph():

    builder = StateGraph(PlannerState)

    builder.add_node("validator", validator_node)

    builder.set_entry_point("validator")
    builder.add_edge("validator", END)

    return builder.compile()
