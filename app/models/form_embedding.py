# app/models/form_embedding.py
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FormEmbedding(Base):
    __tablename__ = "form_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    form_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("form_versions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Qdrant references
    qdrant_point_id = Column(String, nullable=False, unique=True, index=True)
    collection_name = Column(String, nullable=False)
    
    # Embedding metadata for debugging/tracking
    embedding_metadata = Column(JSONB, nullable=True)  # model_name, dimensions, etc.
    
    # Search/retrieval metadata
    is_active = Column(String, default=True)  # Soft delete for embeddings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    form_version = relationship("FormVersion", back_populates="embeddings")

    # Indexes
    __table_args__ = (
        Index('idx_embedding_version', 'form_version_id'),
        Index('idx_embedding_collection', 'collection_name'),
    )