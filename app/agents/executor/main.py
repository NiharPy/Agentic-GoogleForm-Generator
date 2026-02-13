# app/agents/executor/main.py

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.agent_task import AgentTask
from app.models.conversation import Conversation
from app.models.user import User
from app.core.google_forms import create_google_form

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

        logger.info(f"🚀 Executing task {task.id}")

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

            # 4️⃣ Execute form creation
            form_id, form_url = await create_google_form(
                user,
                conversation.form_snapshot,
                db
            )

            # 5️⃣ Update task (DO NOT TOUCH CONVERSATION STATUS)
            task.status = "completed"
            task.result = {
                "form_id": form_id,
                "form_url": form_url,
            }
            task.completed_at = datetime.now(timezone.utc)

            await db.commit()

            logger.info(f"✅ Form created: {form_url}")

        except Exception as e:
            logger.exception("❌ Execution failed")

            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()


if __name__ == "__main__":
    asyncio.run(run_executor())
