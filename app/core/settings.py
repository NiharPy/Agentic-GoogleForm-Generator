# app/core/settings.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""

    # Database
    DATABASE_URL: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # GCP Configuration
    GCP_PROJECT_ID: str
    GCP_LOCATION: str = "us-central1"

    # Gemini Configuration
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GOOGLE_API_KEY: str

    # Embedding Model
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Qdrant (Cloud)
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "form_snapshots"

    # Google Credentials (Optional)
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Singleton instance
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Default instance for backwards compatibility
settings = get_settings()