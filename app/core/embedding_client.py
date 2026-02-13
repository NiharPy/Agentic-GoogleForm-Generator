from openai import AsyncOpenAI
from app.core.settings import settings
import logging
from typing import List

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    OpenAI Embedding client using text-embedding-3-small
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536  # text-embedding-3-small default dimension
        logger.info(f"✅ Initialized OpenAI embedding client with {self.model}")

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding using OpenAI API
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (embedding vector)
        """
        try:
            # Truncate if too long (OpenAI limit is ~8191 tokens)
            if len(text) > 30000:  # Rough character estimate
                logger.warning(f"Text too long ({len(text)} chars), truncating")
                text = text[:30000]
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"✅ Generated embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise Exception(f"Failed to generate embedding: {str(e)}")