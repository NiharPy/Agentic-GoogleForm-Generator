from app.agents.executor.state import ExecutorState
from app.models.agent_task import AgentTask
from app.models.conversation import Conversation
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


async def send_response_node(state: ExecutorState) -> ExecutorState:
    """
    Node 4: Send response back to planner
    
    Actions:
    1. Update original task status
    2. Create response task for planner
    3. Update conversation with form URL
    4. Build response payload
    
    Returns:
        Final state with response_payload
    """
    
    task_id = state.get("task_id")
    conversation_id = state.get("conversation_id")
    status = state.get("status", "failed")
    form_id = state.get("form_id")
    form_url = state.get("form_url")
    error = state.get("error")
    details = state.get("details")
    
    try:
        async with AsyncSessionLocal() as db:
            # 1️⃣ Update original task
            if task_id:
                result = await db.execute(
                    select(AgentTask).where(AgentTask.id == task_id)
                )
                original_task = result.scalar_one_or_none()
                
                if original_task:
                    original_task.status = status
                    original_task.completed_at = datetime.utcnow()
                    
                    logger.info(f"✅ Updated task {task_id} status to '{status}'")
            
            # 2️⃣ Update conversation with form URL
            if conversation_id and status == "completed" and form_url:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conversation = result.scalar_one_or_none()
                
                if conversation:
                    # Store form metadata in executor_state
                    conversation.executor_state = {
                        "form_id": form_id,
                        "form_url": form_url,
                        "created_at": datetime.utcnow().isoformat(),
                        "status": "published"
                    }
                    
                    logger.info(f"✅ Updated conversation {conversation_id} with form URL")
            
            # 3️⃣ Create response task for planner (optional - for notifications)
            if status == "completed":
                response_task = AgentTask(
                    id=uuid.uuid4(),
                    conversation_id=conversation_id,
                    task_type="form_created",
                    source_agent="executor",
                    target_agent="planner",
                    task_payload={
                        "form_id": form_id,
                        "form_url": form_url,
                        "status": "success"
                    },
                    status="pending"
                )
                
                db.add(response_task)
                logger.info(f"📨 Created response task for planner")
            
            elif status == "failed":
                # Send error notification to planner
                response_task = AgentTask(
                    id=uuid.uuid4(),
                    conversation_id=conversation_id,
                    task_type="form_creation_failed",
                    source_agent="executor",
                    target_agent="planner",
                    task_payload={
                        "error": error,
                        "details": details,
                        "status": "failed"
                    },
                    status="pending"
                )
                
                db.add(response_task)
                logger.error(f"📨 Created error response task for planner")
            
            # Commit all changes
            await db.commit()
            
            logger.info("✅ All database updates committed")
        
        # 4️⃣ Build response payload
        if status == "completed":
            response_payload = {
                "success": True,
                "form_id": form_id,
                "form_url": form_url,
                "message": "Form created successfully"
            }
            logger.info(f"🎉 Executor completed successfully: {form_url}")
        else:
            response_payload = {
                "success": False,
                "error": error,
                "details": details,
                "message": "Form creation failed"
            }
            logger.error(f"❌ Executor failed: {error}")
        
        return {
            **state,
            "response_payload": response_payload
        }
    
    except Exception as e:
        logger.error(f"Failed to send response: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error": "response_send_error",
            "details": str(e),
            "response_payload": {
                "success": False,
                "error": "response_send_error",
                "details": str(e)
            }
        }
