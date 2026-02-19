# app/agents/executor/main.py

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.agent_task import AgentTask
from app.models.conversation import Conversation
from app.models.user import User
from app.models.forms import Form
from app.core.google_forms import create_google_form, update_google_form

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def run_executor():

    async with AsyncSessionLocal() as db:

        # 1️⃣ Get next pending task
        result = await db.execute(
            select(AgentTask)
            .where(AgentTask.status == "pending")
            .order_by(AgentTask.created_at)
            .limit(1)
        )

        task = result.scalar_one_or_none()

        if not task:
            logger.info("No pending tasks.")
            return

        logger.info(f"🚀 Executing task {task.id} (type: {task.task_type})")

        # Mark task as in progress
        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # 2️⃣ Load conversation
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == task.conversation_id
                )
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                raise Exception("Conversation not found")

            # 3️⃣ Load user
            result = await db.execute(
                select(User).where(User.id == conversation.user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise Exception("User not found")

            # 4️⃣ Check if form already exists for this conversation
            result = await db.execute(
                select(Form).where(Form.conversation_id == task.conversation_id)
            )
            existing_form = result.scalar_one_or_none()

            # 5️⃣ Execute based on task type and form existence
            if existing_form:
                # UPDATE existing form
                logger.info(f"🔄 Updating existing form: {existing_form.google_form_id}")
                
                form_id, form_url = await update_google_form(
                    user,
                    existing_form.google_form_id,
                    conversation.form_snapshot,
                    db
                )
                
                # Update form record
                existing_form.form_url = form_url
                existing_form.updated_at = datetime.now(timezone.utc)
                
                logger.info(f"✅ Form updated: {form_url}")
                
            else:
                # CREATE new form
                logger.info(f"📝 Creating new form")
                
                form_id, form_url = await create_google_form(
                    user,
                    conversation.form_snapshot,
                    db
                )
                
                # Store form in database
                new_form = Form(
                    google_form_id=form_id,
                    user_id=user.id,
                    conversation_id=task.conversation_id,
                    form_url=form_url
                )
                db.add(new_form)
                
                logger.info(f"✅ Form created: {form_url}")

            # 6️⃣ Update task (DO NOT TOUCH CONVERSATION STATUS)
            task.status = "completed"
            task.result = {
                "form_id": form_id,
                "form_url": form_url,
                "action": "updated" if existing_form else "created"
            }
            task.completed_at = datetime.now(timezone.utc)

            await db.commit()

        except Exception as e:
            logger.exception("❌ Execution failed")

            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()


async def executor_worker_loop(interval: int = 5):
    """
    Continuous worker loop that keeps running
    Checks for pending tasks every N seconds
    
    Handles both:
    - execute_form (from /start) - Creates new form
    - execute_form (from /continue) - Updates existing form
    
    Args:
        interval: Seconds between checks (default: 5)
    """
    logger.info(f"🔄 Executor worker started (polling every {interval}s)")
    logger.info("📝 Handles: CREATE (new conversations) and UPDATE (continue)")
    logger.info("Press Ctrl+C to stop")
    
    while True:
        try:
            await run_executor()
        except Exception as e:
            logger.error(f"❌ Worker loop error: {e}", exc_info=True)
        
        # Wait before next check
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(executor_worker_loop())