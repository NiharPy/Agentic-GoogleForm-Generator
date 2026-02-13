# app/agents/planner/planner_agent.py
import logging
from typing import Dict, Any, List, Optional
from app.agents.planner.graph import planner_graph
from app.agents.planner.state import PlannerState
from datetime import datetime

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Planner Agent using LangGraph
    
    Flow:
    1. Intent Parser -> Extract requirements
    2. Snapshot Creator -> Build form + embed in Qdrant
    3. Validator -> Check completeness + generate follow-ups
    4. A2A Sender -> Send to executor (if complete)
    """
    
    def __init__(self):
        self.graph = planner_graph
    
    async def process(
        self,
        user_prompt: str,
        conversation_id: str,
        uploaded_files: Optional[List[str]] = None,
        existing_snapshot: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute planner pipeline using LangGraph
        
        Args:
            user_prompt: User input text
            conversation_id: Conversation ID
            uploaded_files: Uploaded file paths
            existing_snapshot: Current snapshot if updating
            conversation_history: Previous messages
            
        Returns:
            Complete planner result
        """
        try:
            logger.info(f"🚀 Planner started for conversation {conversation_id}")
            
            # Build initial state
            initial_state: PlannerState = {
                # Input
                "user_prompt": user_prompt,
                "conversation_id": conversation_id,
                "uploaded_files": uploaded_files,
                "existing_snapshot": existing_snapshot,
                "conversation_history": conversation_history,
                
                # Initialize outputs
                "parsed_intent": None,
                "parse_error": None,
                "snapshot": None,
                "snapshot_id": None,
                "embedding_dimensions": None,
                "snapshot_error": None,
                "a2a_message": None,
                "task_id": None,
                "a2a_error": None,
                "is_complete": False,
                "confidence": 0.0,
                "follow_up_questions": [],
                "reasoning": "",
                "validation_error": None,
                "success": False,
                "error": None,
                "timestamp": datetime.utcnow()
            }
            
            # Run graph
            final_state = await self.graph.ainvoke(initial_state)
            
            # Build result from final state
            result = {
                "success": final_state.get("success", True),
                "is_complete": final_state["is_complete"],
                "confidence": final_state["confidence"],
                "snapshot": final_state.get("snapshot"),
                "snapshot_id": final_state.get("snapshot_id"),
                "follow_up_questions": final_state["follow_up_questions"],
                "reasoning": final_state["reasoning"],
                "a2a_message": final_state.get("a2a_message"),
                "task_id": final_state.get("task_id"),
                "error": final_state.get("error"),
                "timestamp": final_state["timestamp"]
            }
            
            logger.info(
                f"✅ Planner complete. "
                f"Complete: {result['is_complete']}, "
                f"Confidence: {result['confidence']:.2f}, "
                f"Follow-ups: {len(result['follow_up_questions'])}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Planner failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }


# Singleton
_planner_agent: Optional[PlannerAgent] = None


def get_planner_agent() -> PlannerAgent:
    """Get or create planner agent"""
    global _planner_agent
    if _planner_agent is None:
        _planner_agent = PlannerAgent()
    return _planner_agent