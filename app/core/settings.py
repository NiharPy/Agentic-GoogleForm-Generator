from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):

    # Database
    DATABASE_URL: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET : str
    JWT_SECRET: str
    GOOGLE_REDIRECT_URI : str
    JWT_ALGORITHM: str


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

# Cache settings so it's loaded only once
@lru_cache
def get_settings():
    return Settings()
