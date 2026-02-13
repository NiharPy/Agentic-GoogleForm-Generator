# app/models/form.py (UPDATED - with index)
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Form(Base):
    __tablename__ = "forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    google_form_id = Column(String, nullable=False, unique=True, index=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE")
    )

    form_url = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="forms")
    conversation = relationship("Conversation", back_populates="forms")

    versions = relationship(
        "FormVersion",
        back_populates="form",
        cascade="all, delete-orphan",
        order_by="FormVersion.version_number"
    )

    # Indexes
    __table_args__ = (
        Index('idx_form_conversation', 'conversation_id'),
        Index('idx_form_user', 'user_id'),
    )