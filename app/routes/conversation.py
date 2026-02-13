from fastapi import APIRouter, Depends, HTTPException, status
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


# ✅ Start New Conversation with a prompt
@router.post("/start", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1️⃣ Create conversation
    conversation = Conversation(
        user_id=current_user.id,
        title=body.prompt,
        status="active",
        current_version=0
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # 2️⃣ Invoke Planner Agent
    await planner_graph.ainvoke({
        "user_prompt": body.prompt,
        "documents": None,
        "form_snapshot": None,
        "conversation_id": str(conversation.id)
    })

    # 3️⃣ Return immediately
    return conversation


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
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Continue an existing conversation with a new message
    """
    # 1️⃣ Validate conversation exists and belongs to user
    conversation = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = conversation.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # 2️⃣ Check if conversation is still active
    if conversation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot continue conversation with status: {conversation.status}"
        )
    
    # 3️⃣ Retrieve current form snapshot from Qdrant (if exists)
    qdrant_client = QdrantClient()
    form_data = await qdrant_client.get_by_conversation(conversation_id)
    form_snapshot = form_data.get("form_snapshot") if form_data else None
    
    logger.info(f"📋 Current form has {len(form_snapshot.get('fields', [])) if form_snapshot else 0} fields")
    
    # 4️⃣ Invoke Planner Agent and WAIT for completion
    logger.info(f"🤖 Invoking planner with message: {body.message}")
    
    start_time = time.time()
    
    result = await planner_graph.ainvoke({
        "user_prompt": body.message,
        "documents": body.documents,
        "form_snapshot": form_snapshot,
        "conversation_id": conversation_id,
        "is_continuation": True
    })
    
    elapsed = time.time() - start_time
    logger.info(f"✅ Planner completed in {elapsed:.2f}s")
    
    # 5️⃣ Check if planner succeeded
    if result.get("error"):
        logger.error(f"Planner error: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Form generation failed: {result.get('error')}"
        )
    
    # 6️⃣ Refresh conversation from DB to get updated snapshot
    await db.refresh(conversation)
    
    # 7️⃣ Also get from Qdrant (should match DB now)
    updated_form_data = await qdrant_client.get_by_conversation(conversation_id)
    updated_snapshot = updated_form_data.get("form_snapshot") if updated_form_data else None
    
    # Use DB snapshot as primary source (more reliable)
    final_snapshot = conversation.form_snapshot or updated_snapshot
    
    logger.info(f"📋 Updated form has {len(final_snapshot.get('fields', [])) if final_snapshot else 0} fields")
    
    # 8️⃣ Update conversation metadata
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    
    # 9️⃣ Return updated conversation with new snapshot
    return {
        "conversation_id": str(conversation.id),
        "status": conversation.status,
        "message": "Form updated successfully",
        "form_snapshot": final_snapshot,
        "field_count": len(final_snapshot.get("fields", [])) if final_snapshot else 0,
        "processing_time": f"{elapsed:.2f}s",
        "timestamp": conversation.updated_at
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
