from qdrant_client import QdrantClient as QClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.settings import settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QdrantClient:
    """Enhanced Qdrant client for OpenAI embeddings"""

    def __init__(self):
        # Use cloud Qdrant with API key authentication
        self.client = QClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.vector_size = 1536  # text-embedding-3-small dimension
        
        # Ensure collection exists with correct dimensions
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist or recreate if dimensions mismatch"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                # Check if dimensions match
                collection_info = self.client.get_collection(self.collection_name)
                existing_size = collection_info.config.params.vectors.size
                
                if existing_size != self.vector_size:
                    logger.warning(
                        f"⚠️ Collection '{self.collection_name}' has wrong dimensions "
                        f"(expected {self.vector_size}, got {existing_size}). "
                        f"Deleting and recreating..."
                    )
                    # Delete old collection
                    self.client.delete_collection(self.collection_name)
                    logger.info(f"🗑️ Deleted old collection '{self.collection_name}'")
                    
                    # Create new collection with correct dimensions
                    self._create_collection()
                else:
                    logger.info(f"Collection {self.collection_name} already exists with correct dimensions")
            else:
                # Collection doesn't exist, create it
                self._create_collection()
                
        except Exception as e:
            logger.error(f"Collection check/creation error: {e}")
            # Try to create anyway
            try:
                self._create_collection()
            except:
                logger.error("Failed to create collection even after retry")
    
    def _create_collection(self):
        """Create the collection with proper vector configuration"""
        logger.info(f"Creating Qdrant collection: {self.collection_name} (dimension: {self.vector_size})")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            )
        )
        logger.info(f"✅ Collection {self.collection_name} created successfully")

    async def store_embedding(
        self,
        conversation_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """
        Store form snapshot embedding in Qdrant
        
        Args:
            conversation_id: Unique conversation identifier (used as point ID)
            vector: Embedding vector (1536 dimensions for text-embedding-3-small)
            payload: Form snapshot data
            
        Returns:
            True if successful
        """
        try:
            # Validate vector dimension
            if len(vector) != self.vector_size:
                raise ValueError(
                    f"Vector dimension mismatch: expected {self.vector_size}, got {len(vector)}"
                )
            
            point = PointStruct(
                id=conversation_id,
                vector=vector,
                payload={
                    "conversation_id": conversation_id,
                    "form_snapshot": payload,
                    "snapshot_type": "form_schema"
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✅ Stored embedding for conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            raise

    async def retrieve_similar(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar form snapshots based on query embedding
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar form snapshots with scores
        """
        try:
            # Try newer API first (qdrant-client >= 1.8.0)
            try:
                search_result = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
                # Extract points from result
                results = search_result.points if hasattr(search_result, 'points') else search_result
                
            except (AttributeError, TypeError):
                # Fallback to older API (qdrant-client < 1.8.0)
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
            
            similar_forms = []
            for result in results:
                similar_forms.append({
                    "conversation_id": result.payload.get("conversation_id"),
                    "form_snapshot": result.payload.get("form_snapshot"),
                    "score": result.score
                })
            
            logger.info(f"✅ Retrieved {len(similar_forms)} similar forms")
            return similar_forms
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar forms: {e}")
            return []

    async def get_by_conversation(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific form snapshot by conversation ID
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Form snapshot if found, None otherwise
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[conversation_id]
            )
            
            if result:
                return {
                    "conversation_id": result[0].payload.get("conversation_id"),
                    "form_snapshot": result[0].payload.get("form_snapshot")
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to retrieve conversation {conversation_id}: {e}")
            return None

    async def delete_by_conversation(
        self,
        conversation_id: str
    ) -> bool:
        """
        Delete embedding by conversation ID
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[conversation_id]
            )
            
            logger.info(f"✅ Deleted embedding for conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            return False