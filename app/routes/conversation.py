from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.core.security import get_current_user
from app.schemas.conversation import ConversationCreate
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.planner.graph import build_planner_graph

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)

planner_graph = build_planner_graph()


# Background task to trigger executor
async def trigger_executor_for_conversation(conversation_id: str):
    """
    Background task that triggers executor after planner completes
    
    Flow:
    1. Wait for planner to create AgentTask
    2. Executor worker picks up task
    3. MCP creates Google Form
    4. Updates conversation with form URL
    """
    try:
        # Small delay to ensure AgentTask is committed
        import asyncio
        await asyncio.sleep(1)
        
        # Executor worker will process the task
        # No action needed here - just logging
        logger.info(f"🚀 Executor triggered for conversation {conversation_id}")
        logger.info("ℹ️ Executor worker will process AgentTask in background")
        
    except Exception as e:
        logger.error(f"Failed to trigger executor: {e}")


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Start a new conversation and generate form
    
    Flow:
    1. Create conversation in DB
    2. Invoke planner (creates form_snapshot)
    3. Planner creates AgentTask for executor
    4. Background: Executor worker processes task
    5. Executor calls MCP to create Google Form
    6. Updates conversation with form URL
    
    Returns conversation immediately - executor runs in background
    """
    
    # 1️⃣ Create conversation
    logger.info(f"📝 Creating new conversation for user {current_user.id}")
    
    conversation = Conversation(
        user_id=current_user.id,
        title=body.prompt,
        status="active",
        current_version=0
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    conversation_id = str(conversation.id)
    logger.info(f"✅ Created conversation {conversation_id}")

    # 2️⃣ Invoke Planner Agent (blocks until form_snapshot created)
    logger.info(f"🤖 Invoking planner: '{body.prompt}'")
    
    start_time = time.time()
    
    try:
        result = await planner_graph.ainvoke({
            "user_prompt": body.prompt,
            "documents": None,
            "form_snapshot": None,
            "conversation_id": conversation_id
        })
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Planner completed in {elapsed:.2f}s")
        
        # Check for errors
        if result.get("error"):
            logger.error(f"Planner error: {result['error']}")
            conversation.status = "failed"
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Form generation failed: {result.get('error')}"
            )
        
        # 3️⃣ Planner has created AgentTask - executor will pick it up
        logger.info(f"📨 AgentTask created for executor")
        
        # Trigger executor in background
        background_tasks.add_task(trigger_executor_for_conversation, conversation_id)
        
        # 4️⃣ Refresh conversation to get form_snapshot
        await db.refresh(conversation)
        
        logger.info(
            f"✅ Conversation created. "
            f"Form snapshot: {len(conversation.form_snapshot.get('fields', [])) if conversation.form_snapshot else 0} fields. "
            f"Executor running in background."
        )
        
    except Exception as e:
        logger.error(f"Failed to invoke planner: {e}", exc_info=True)
        conversation.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate form: {str(e)}"
        )

    # 5️⃣ Return conversation
    # Note: form_url will be populated later by executor
    return {
        "id": conversation_id,
        "title": conversation.title,
        "status": conversation.status,
        "form_snapshot": conversation.form_snapshot,
        "executor_status": "processing",  # Executor running in background
        "message": "Form schema created. Google Form creation in progress.",
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at
    }



from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from datetime import datetime
from app.core.qdrant_client import QdrantClient
import logging

logger = logging.getLogger(__name__)

# Request schema
class ConversationContinue(BaseModel):
    message: str
    documents: Optional[List[str]] = None  # Optional document IDs or content


import time

@router.post("/{conversation_id}/continue", status_code=status.HTTP_200_OK)
async def continue_conversation(
    conversation_id: str,
    body: ConversationContinue,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Continue an existing conversation and update form schema.

    Flow:
    1. Validate conversation
    2. Invoke planner with existing form_snapshot
    3. Planner updates form_snapshot
    4. Planner creates AgentTask
    5. Background: Executor worker processes task
    """

    # 1️⃣ Validate conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot continue conversation with status: {conversation.status}"
        )

    logger.info(f"✏️ Continuing conversation {conversation_id}")

    current_field_count = (
        len(conversation.form_snapshot.get("fields", []))
        if conversation.form_snapshot
        else 0
    )

    # 2️⃣ Invoke Planner
    start_time = time.time()

    try:
        result = await planner_graph.ainvoke({
            "user_prompt": body.message,
            "documents": body.documents,
            "form_snapshot": conversation.form_snapshot,
            "conversation_id": conversation_id,
            "is_continuation": True
        })

        elapsed = time.time() - start_time
        logger.info(f"✅ Planner completed in {elapsed:.2f}s")

        # Handle planner error
        if result.get("error"):
            conversation.status = "failed"
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Form update failed: {result.get('error')}"
            )

        # 3️⃣ Refresh updated snapshot
        await db.refresh(conversation)

        new_field_count = (
            len(conversation.form_snapshot.get("fields", []))
            if conversation.form_snapshot
            else 0
        )

        # 4️⃣ Update metadata
        conversation.current_version += 1
        conversation.updated_at = datetime.utcnow()
        await db.commit()

        logger.info(f"📋 Fields updated: {current_field_count} → {new_field_count}")

        # 5️⃣ Trigger executor (same pattern as /start)
        background_tasks.add_task(
            trigger_executor_for_conversation,
            conversation_id
        )

        logger.info("🚀 Executor running in background")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to continue conversation: {e}", exc_info=True)
        conversation.status = "failed"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update form: {str(e)}"
        )

    # 6️⃣ Return immediately
    return {
        "id": conversation_id,
        "status": conversation.status,
        "version": conversation.current_version,
        "form_snapshot": conversation.form_snapshot,
        "field_count": new_field_count,
        "field_change": f"{current_field_count} → {new_field_count}",
        "executor_status": "processing",
        "message": "Form schema updated. Google Form update in progress.",
        "processing_time": f"{elapsed:.2f}s",
        "updated_at": conversation.updated_at
    }



# ✅ Get All Conversations for Current User
@router.get("/", response_model=List[dict])
def get_user_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )

    return conversations


# ✅ Get Single Conversation
@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return conversation


# ✅ Delete Conversation
@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    db.delete(conversation)
    db.commit()

    return {"message": "Conversation deleted successfully"}
