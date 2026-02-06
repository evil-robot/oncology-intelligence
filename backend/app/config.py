"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = ""

    # OpenAI (optional - needed for embeddings)
    openai_api_key: str = ""

    # SerpAPI (for Google Trends data)
    serpapi_key: str = ""

    # Azure Storage (optional)
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "pediatric-oncology-data"

    # App
    environment: str = "development"
    log_level: str = "INFO"

    # Basic Auth (optional - set to enable password protection)
    basic_auth_username: str = ""
    basic_auth_password: str = ""

    # Embedding config
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
