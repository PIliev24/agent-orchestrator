"""Configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Authentication
    api_key: str = "default-api-key"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_orchestrator"
    database_echo: bool = False

    # Sync database URL for Alembic migrations
    @property
    def database_url_sync(self) -> str:
        """Return sync database URL for Alembic."""
        return self.database_url.replace("+asyncpg", "")

    # AI Provider Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    mistral_api_key: str | None = None

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # LangGraph Checkpointing
    checkpoint_connection_string: str | None = None

    @property
    def checkpoint_db_uri(self) -> str:
        """Return checkpoint database URI (uses psycopg format)."""
        if self.checkpoint_connection_string:
            return self.checkpoint_connection_string
        # Convert asyncpg URL to psycopg format for LangGraph checkpointer
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
