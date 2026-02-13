# app/models/conversation.py (UPDATED)
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Conversation metadata
    title = Column(String, nullable=True)
    status = Column(String, default="active")  # 'active', 'completed', 'archived'

    # 🔥 Active working state (AI draft before publishing to Google)
    form_snapshot = Column(JSONB, nullable=True)  # Current working version
    current_version = Column(Integer, default=0)

    # File tracking
    uploaded_files = Column(JSONB, nullable=True)  # [{filename, type, storage_path, size}]
    
    # Agent state tracking
    planner_state = Column(JSONB, nullable=True)  # Current planner understanding/context
    executor_state = Column(JSONB, nullable=True)  # Current executor state
    
    # Follow-up question tracking
    pending_questions = Column(JSONB, nullable=True)  # Questions awaiting user response
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="conversations")
    
    forms = relationship(
        "Form",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at"
    )
    
    agent_tasks = relationship(
        "AgentTask",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentTask.created_at"
    )

    # Indexes
    __table_args__ = (
        Index('idx_conv_user_status', 'user_id', 'status'),
        Index('idx_conv_updated', 'updated_at'),
        Index('idx_conv_created', 'created_at'),
    )