# app/workers/executor_worker.py
"""
Background worker that processes executor tasks
Can be run as:
1. Separate process
2. FastAPI background task
3. Celery task
4. Scheduled cron job
"""

import asyncio
import logging
from sqlalchemy import select
from app.models.agent_task import AgentTask
from app.core.database import AsyncSessionLocal
from app.agents.executor.executor_agent import get_executor_agent
from datetime import datetime

logger = logging.getLogger(__name__)


async def process_pending_executor_tasks():
    """
    Find and process all pending executor tasks
    """
    executor = get_executor_agent()
    
    try:
        async with AsyncSessionLocal() as db:
            # Find pending tasks for executor
            result = await db.execute(
                select(AgentTask).where(
                    AgentTask.target_agent == "executor",
                    AgentTask.status == "pending",
                    AgentTask.task_type == "execute_form"
                ).order_by(AgentTask.created_at)
            )
            
            pending_tasks = result.scalars().all()
            
            if not pending_tasks:
                logger.debug("No pending executor tasks")
                return
            
            logger.info(f"📋 Found {len(pending_tasks)} pending executor tasks")
            
            for task in pending_tasks:
                try:
                    # Mark as processing
                    task.status = "processing"
                    task.started_at = datetime.utcnow()
                    await db.commit()
                    
                    logger.info(f"⚙️ Processing task {task.id}")
                    
                    # Execute task
                    result = await executor.process(str(task.id))
                    
                    # Update task status
                    if result["success"]:
                        task.status = "completed"
                        logger.info(f"✅ Task {task.id} completed")
                    else:
                        task.status = "failed"
                        logger.error(f"❌ Task {task.id} failed: {result.get('error')}")
                    
                    task.completed_at = datetime.utcnow()
                    await db.commit()
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process task {task.id}: {e}", exc_info=True)
                    task.status = "failed"
                    task.completed_at = datetime.utcnow()
                    await db.commit()
                    await db.rollback()
                    continue
    
    except Exception as e:
        logger.error(f"❌ Executor worker error: {e}", exc_info=True)


async def executor_worker_loop(interval: int = 5):
    """
    Continuous worker loop that checks for tasks every N seconds
    
    Args:
        interval: Seconds between checks
    """
    logger.info(f"🔄 Executor worker started (checking every {interval}s)")
    
    while True:
        try:
            await process_pending_executor_tasks()
        except Exception as e:
            logger.error(f"❌ Worker loop error: {e}", exc_info=True)
        
        await asyncio.sleep(interval)


# For running as standalone script
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(executor_worker_loop())
