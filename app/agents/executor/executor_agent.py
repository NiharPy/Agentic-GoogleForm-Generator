# app/agents/executor/executor_agent.py
import logging
from typing import Dict, Any, Optional
from app.agents.executor.graph import executor_graph
from app.agents.executor.state import ExecutorState
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Executor Agent using LangGraph
    
    Flow:
    1. Extract Task -> Get form snapshot and credentials from database
    2. Convert to Google Forms -> Transform to Google Forms API format
    3. Execute Forms API -> Create form via Google API
    4. Send Response -> Update database and notify planner
    """
    
    def __init__(self):
        self.graph = executor_graph
        logger.info("✅ ExecutorAgent initialized")
    
    async def process(self, task_id: str) -> Dict[str, Any]:
        """
        Execute form creation pipeline using LangGraph
        
        Args:
            task_id: AgentTask ID to process
            
        Returns:
            Complete executor result with form_id and form_url
        """
        try:
            logger.info(f"🚀 Executor started for task {task_id}")
            
            # Build initial state
            initial_state: ExecutorState = {
                "task_id": task_id,
                "status": "pending"
            }
            
            # Run graph
            final_state = await self.graph.ainvoke(initial_state)
            
            # Extract result
            result = {
                "success": final_state.get("status") == "completed",
                "form_id": final_state.get("form_id"),
                "form_url": final_state.get("form_url"),
                "error": final_state.get("error"),
                "details": final_state.get("details"),
                "response_payload": final_state.get("response_payload"),
                "timestamp": datetime.utcnow()
            }
            
            if result["success"]:
                logger.info(
                    f"✅ Executor complete. "
                    f"Form ID: {result['form_id']}, "
                    f"URL: {result['form_url']}"
                )
            else:
                logger.error(
                    f"❌ Executor failed. "
                    f"Error: {result['error']}, "
                    f"Details: {result['details']}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Executor failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "executor_exception",
                "details": str(e),
                "timestamp": datetime.utcnow()
            }


# Singleton
_executor_agent: Optional[ExecutorAgent] = None


def get_executor_agent() -> ExecutorAgent:
    """Get or create executor agent"""
    global _executor_agent
    if _executor_agent is None:
        _executor_agent = ExecutorAgent()
    return _executor_agent