"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars from other projects
    )

    # Authentication - either token or email/password
    monarch_token: str | None = None
    monarch_email: str | None = None
    monarch_password: str | None = None

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # API settings
    api_prefix: str = ""

    # Database settings
    database_url: str | None = None  # Full URL takes precedence
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "monarch"
    database_user: str = "monarch"
    database_password: str = ""

    # Sync settings
    sync_enabled: bool = True
    sync_interval_minutes: int = 60

    @property
    def has_token_auth(self) -> bool:
        """Check if token authentication is configured."""
        return self.monarch_token is not None

    @property
    def has_credential_auth(self) -> bool:
        """Check if email/password authentication is configured."""
        return self.monarch_email is not None and self.monarch_password is not None

    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        if self.database_url:
            # Convert postgres:// to postgresql+asyncpg://
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


settings = Settings()
