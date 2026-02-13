# app/models/agent_task.py
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Task identification
    task_type = Column(String, nullable=False)  # 'parse_data', 'generate_questions', 'update_form', 'validate_form'
    source_agent = Column(String, nullable=False)  # 'planner', 'executor', 'system'
    target_agent = Column(String, nullable=False)  # 'planner', 'executor'
    
    # Task data
    task_payload = Column(JSONB, nullable=False)  # Input data for the task
    result = Column(JSONB, nullable=True)  # Output/result of the task
    
    # Status tracking
    status = Column(String, default="pending")  # 'pending', 'in_progress', 'completed', 'failed'
    error_message = Column(Text, nullable=True)  # Error details if failed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agent_tasks")

    # Indexes
    __table_args__ = (
        Index('idx_task_conversation_status', 'conversation_id', 'status'),
        Index('idx_task_created', 'created_at'),
        Index('idx_task_source_target', 'source_agent', 'target_agent'),
    )