from __future__ import annotations

from contextclaw.settings import settings


class OpenAIProvider:
    """Embedding provider using OpenAI's API."""

    model: str
    dim: int

    def __init__(
        self,
        model: str | None = None,
        dim: int | None = None,
    ) -> None:
        self.model = model or settings.openai_embedding_model
        self.dim = dim or settings.openai_embedding_dim
        self._client = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        import openai

        client = self._get_client()
        response = client.embeddings.create(input=texts, model=self.model)
        sorted_data = sorted(response.data, key=lambda d: d.index)
        return [d.embedding for d in sorted_data]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=settings.openai_api_key)
        return self._client


class DeepSeekProvider:
    """Embedding provider using DeepSeek's API (OpenAI-compatible)."""

    model: str
    dim: int

    def __init__(
        self,
        model: str | None = None,
        dim: int | None = None,
    ) -> None:
        self.model = model or settings.deepseek_embedding_model
        self.dim = dim or settings.deepseek_embedding_dim
        self._client = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = client.embeddings.create(input=texts, model=self.model)
        sorted_data = sorted(response.data, key=lambda d: d.index)
        return [d.embedding for d in sorted_data]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            )
        return self._client
