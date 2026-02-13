# app/models/conversation_message.py
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Message metadata
    role = Column(String, nullable=False)  # 'user', 'planner', 'executor', 'system'
    content = Column(Text, nullable=False)
    
    # A2A Protocol metadata
    a2a_metadata = Column(JSONB, nullable=True)  # task_id, dependencies, protocol version, etc.
    
    # Link to form version if this message resulted in an update
    form_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("form_versions.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    form_version = relationship("FormVersion", back_populates="messages")