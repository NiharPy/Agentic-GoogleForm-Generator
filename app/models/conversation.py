import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
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

    title = Column(String, nullable=True)
    status = Column(String, default="active")

    # 🔥 Active working state (AI draft before publishing to Google)
    form_snapshot = Column(JSONB, nullable=True)
    current_version = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="conversations")

    # One conversation → many forms
    forms = relationship(
        "Form",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
