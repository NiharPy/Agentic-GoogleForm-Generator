from langgraph.graph import StateGraph, END
from app.agents.planner.state import PlannerState
from app.agents.planner.nodes.intent_parser import intent_parser_node
from app.agents.planner.nodes.llm_inference import llm_inference_node
from app.agents.planner.nodes.a2a_sender import a2a_sender_node


def build_planner_graph():

    builder = StateGraph(PlannerState)

    builder.add_node("intent_parser", intent_parser_node)
    builder.add_node("llm_inference", llm_inference_node)
    builder.add_node("a2a_sender", a2a_sender_node)

    builder.set_entry_point("intent_parser")

    builder.add_edge("intent_parser", "llm_inference")

    # 🔥 CONDITIONAL EDGE - Fixed routing function
    def route_after_llm(state: PlannerState) -> str:
        """Route based on whether llm_inference had an error"""
        if state.get("error"):
            return "error"
        return "success"

    builder.add_conditional_edges(
        "llm_inference",
        route_after_llm,
        {
            "success": "a2a_sender",
            "error": END
        }
    )

    builder.add_edge("a2a_sender", END)

    return builder.compile()