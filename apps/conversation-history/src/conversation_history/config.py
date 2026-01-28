"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI settings for embeddings
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimensions: int = 1536

    # Server settings
    debug: bool = False

    # Database settings
    database_url: str | None = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "conversation_history"
    database_user: str = "postgres"
    database_password: str = ""

    # Indexing settings
    projects_root: str = "/Users/michaelzakany/projects"
    chunk_size: int = 3000
    chunk_overlap: int = 500

    # Agent Progress source database (for importing)
    source_database_url: str | None = None
    source_database_host: str = "localhost"
    source_database_port: int = 5432
    source_database_name: str = "agent_progress"
    source_database_user: str = "agent_progress"
    source_database_password: str = ""

    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def has_database(self) -> bool:
        """Check if database is configured."""
        return bool(self.database_url or self.database_password)

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI is configured."""
        return self.openai_api_key is not None

    @property
    def async_source_database_url(self) -> str:
        """Get async database URL for source database (agent-progress)."""
        if self.source_database_url:
            url = self.source_database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.source_database_user}:{self.source_database_password}"
            f"@{self.source_database_host}:{self.source_database_port}/{self.source_database_name}"
        )

    @property
    def has_source_database(self) -> bool:
        """Check if source database (agent-progress) is configured."""
        return bool(self.source_database_url or self.source_database_password)


settings = Settings()
