from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "info"
    debug: bool = False

    # ── Auth ──────────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    clerk_publishable_key: str = ""

    # ── Internal service URLs ─────────────────────────────────────
    chat_service_url: str = "http://chat-service:8001"
    search_service_url: str = "http://search-service:8002"
    ingest_service_url: str = "http://ingest-service:8003"
    memory_service_url: str = "http://memory-service:8004"
    graph_service_url: str = "http://graph-service:8005"
    agent_orchestrator_url: str = "http://agent-orchestrator:8006"

    # ── Observability ─────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "contextclaw-api-gateway"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()

# Ensure .env is loaded from project root
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)
