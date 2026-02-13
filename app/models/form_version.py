# app/models/form_version.py (UPDATED)
import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FormVersion(Base):
    __tablename__ = "form_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    form_id = Column(
        UUID(as_uuid=True),
        ForeignKey("forms.id", ondelete="CASCADE"),
        nullable=True  # Nullable because versions can exist before Google Form is created
    )

    # Version tracking
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)  # Complete form structure
    
    # Change tracking
    change_summary = Column(String, nullable=True)  # "Added 3 questions", "Modified question 2 options"
    change_type = Column(String, nullable=True)  # 'initial', 'question_added', 'option_modified', 'structure_changed'
    
    # Agent attribution
    created_by_agent = Column(String, nullable=True)  # 'planner', 'executor', 'user'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    form = relationship("Form", back_populates="versions")
    embeddings = relationship(
        "FormEmbedding",
        back_populates="form_version",
        cascade="all, delete-orphan"
    )
    messages = relationship("ConversationMessage", back_populates="form_version")

    # Indexes
    __table_args__ = (
        Index('idx_version_form_number', 'form_id', 'version_number'),
        Index('idx_version_created', 'created_at'),
    )