from app.agents.executor.state import ExecutorState
from app.models.agent_task import AgentTask
from app.models.conversation import Conversation
from app.models.user import User
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def extract_task_node(state: ExecutorState) -> ExecutorState:
    """
    Node 1: Extract information from AgentTask
    
    Fetches:
    - Task details from database
    - Form snapshot from conversation
    - User credentials for Google API
    
    Returns:
        Updated state with form_snapshot and credentials
    """
    
    task_id = state.get("task_id")
    
    if not task_id:
        logger.error("No task_id provided to executor")
        return {
            **state,
            "status": "failed",
            "error": "missing_task_id",
            "details": "Task ID is required"
        }
    
    try:
        async with AsyncSessionLocal() as db:
            # 1️⃣ Fetch the agent task
            result = await db.execute(
                select(AgentTask).where(AgentTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {
                    **state,
                    "status": "failed",
                    "error": "task_not_found"
                }
            
            logger.info(f"📥 Fetched task {task_id} for conversation {task.conversation_id}")
            
            # 2️⃣ Fetch the conversation
            result = await db.execute(
                select(Conversation).where(Conversation.id == task.conversation_id)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                logger.error(f"Conversation {task.conversation_id} not found")
                return {
                    **state,
                    "status": "failed",
                    "error": "conversation_not_found"
                }
            
            # 3️⃣ Fetch user credentials
            result = await db.execute(
                select(User).where(User.id == conversation.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {conversation.user_id} not found")
                return {
                    **state,
                    "status": "failed",
                    "error": "user_not_found"
                }
            
            # 4️⃣ Check for Google credentials
            if not user.google_access_token or not user.google_refresh_token:
                logger.error(f"User {user.id} missing Google credentials")
                return {
                    **state,
                    "status": "failed",
                    "error": "missing_google_credentials",
                    "details": "User needs to authenticate with Google"
                }
            
            # 5️⃣ Extract form snapshot from task payload
            form_snapshot = task.task_payload
            
            if not form_snapshot:
                logger.error("Task payload is empty")
                return {
                    **state,
                    "status": "failed",
                    "error": "empty_form_snapshot"
                }
            
            logger.info(f"✅ Extracted form snapshot with {len(form_snapshot.get('fields', []))} fields")
            
            # 6️⃣ Return enriched state
            return {
                **state,
                "conversation_id": str(task.conversation_id),
                "form_snapshot": form_snapshot,
                "access_token": user.google_access_token,
                "refresh_token": user.google_refresh_token,
                "status": "processing"
            }
    
    except Exception as e:
        logger.error(f"Failed to extract task info: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error": "extraction_error",
            "details": str(e)
        }
