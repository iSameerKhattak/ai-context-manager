from __future__ import annotations

from contextclaw.embeddings.base import EmbeddingProvider
from contextclaw.embeddings.providers import DeepSeekProvider, OpenAIProvider
from contextclaw.settings import settings


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider based on settings."""
    provider_name = settings.embedding_provider.lower()

    if provider_name == "openai":
        return OpenAIProvider(
            model=settings.openai_embedding_model,
            dim=settings.openai_embedding_dim,
        )
    elif provider_name == "deepseek":
        return DeepSeekProvider(
            model=settings.deepseek_embedding_model,
            dim=settings.deepseek_embedding_dim,
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider_name}")
