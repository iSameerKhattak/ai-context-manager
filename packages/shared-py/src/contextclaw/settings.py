from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global ContextClaw configuration.

    Loads from environment variables with optional .env file support.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://localhost:5432/contextclaw"
    database_url_sync: str = "postgresql+psycopg2://localhost:5432/contextclaw"

    # ── Clerk Auth ──────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # ── GitHub App ──────────────────────────────────────────────────
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    # ── Embedding Providers ─────────────────────────────────────────
    embedding_provider: str = "openai"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dim: int = 1536
    deepseek_api_key: str = ""
    deepseek_embedding_model: str = "deepseek-text-embedding-v2"
    deepseek_embedding_dim: int = 1024
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # ── Qdrant ──────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # ── RabbitMQ ────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"


settings = Settings()
