import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_task import AgentTask
from app.core.database import AsyncSessionLocal
from app.agents.planner.state import PlannerState
import logging

logger = logging.getLogger(__name__)


async def a2a_sender_node(state: PlannerState) -> PlannerState:
    """
    Creates an AgentTask from planner output.
    Async-safe version with defensive key checking.
    """

    # Defensive check - this node should never be called if llm_output is missing
    if "llm_output" not in state or state["llm_output"] is None:
        logger.error("a2a_sender called without llm_output in state")
        return {
            **state,
            "error": "a2a_sender_missing_llm_output",
            "details": "a2a_sender was called without llm_output in state"
        }

    async with AsyncSessionLocal() as db:
        try:
            task = AgentTask(
                id=uuid.uuid4(),
                conversation_id=state["conversation_id"],
                task_type="execute_form",
                source_agent="planner",
                target_agent="executor",  # ✅ Added required field
                task_payload=state["llm_output"],  # ✅ Fixed field name (was 'payload')
            )

            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            logger.info(f"✅ Created agent task {task.id} for conversation {state['conversation_id']}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create agent task: {e}")
            return {
                **state,
                "error": "a2a_sender_db_error",
                "details": str(e)
            }

    return state