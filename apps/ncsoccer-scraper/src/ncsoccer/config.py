"""Configuration settings for NC Soccer scraper using pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="NCSOCCER_DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "192.168.68.103"
    port: int = 5432
    name: str = "ncsoccer"
    user: str = "convo_user"
    password: str = "convo_password"

    @property
    def url(self) -> str:
        """Get the database connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class OpenAISettings(BaseSettings):
    """OpenAI configuration for embeddings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: Optional[str] = None

    @property
    def api_key(self) -> Optional[str]:
        """Get the OpenAI API key."""
        return self.openai_api_key


class Settings(BaseSettings):
    """Combined settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nested settings
    database: DatabaseSettings = DatabaseSettings()
    openai: OpenAISettings = OpenAISettings()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


@lru_cache
def get_database_settings() -> DatabaseSettings:
    """Get cached database settings instance."""
    return DatabaseSettings()


@lru_cache
def get_openai_settings() -> OpenAISettings:
    """Get cached OpenAI settings instance."""
    return OpenAISettings()
