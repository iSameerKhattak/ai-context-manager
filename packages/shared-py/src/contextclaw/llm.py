from __future__ import annotations

import json
from typing import Any

from contextclaw.settings import settings


class LLMRouter:
    """Routes chat completion requests to the configured LLM provider.

    Supports OpenAI and DeepSeek (OpenAI-compatible API).
    """

    def __init__(self) -> None:
        self._openai_client = None
        self._deepseek_client = None

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> str | None:
        """Send a chat completion request and return the response text."""
        import openai

        client, actual_model = self._resolve_client(model)

        kwargs: dict[str, Any] = {
            "model": actual_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if stream:
            kwargs["stream"] = True
            response = client.chat.completions.create(**kwargs)
            parts: list[str] = []
            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    parts.append(delta.content)
            return "".join(parts) or None

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _resolve_client(self, model: str | None):
        """Return (client, model_name) based on settings."""
        import openai

        policy = settings.llm_router_policy or "openai"

        if policy == "deepseek" or (policy == "openai" and model and "deepseek" in model):
            if self._deepseek_client is None:
                self._deepseek_client = openai.OpenAI(
                    api_key=settings.deepseek_api_key or settings.openai_api_key,
                    base_url=settings.deepseek_base_url,
                )
            return self._deepseek_client, model or "deepseek-chat"

        if self._openai_client is None:
            self._openai_client = openai.OpenAI(api_key=settings.openai_api_key)
        return self._openai_client, model or "gpt-4o-mini"

    def build_rag_messages(
        self,
        system_prompt: str,
        context_chunks: list[dict[str, Any]],
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build a message list for RAG: system prompt with context + history + user query."""
        context_text = "\n\n".join(
            f"[{c.get('path', 'unknown')}] (score={c.get('score', 0):.2f})\n{c.get('snippet', '')}"
            for c in context_chunks
        )

        system = f"{system_prompt}\n\nRelevant context:\n{context_text}" if context_chunks else system_prompt

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_query})
        return messages

    def rag_complete(
        self,
        system_prompt: str,
        context_chunks: list[dict[str, Any]],
        user_query: str,
        conversation_history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ) -> str | None:
        """RAG completion: build context-augmented messages and complete."""
        messages = self.build_rag_messages(
            system_prompt=system_prompt,
            context_chunks=context_chunks,
            user_query=user_query,
            conversation_history=conversation_history,
        )
        return self.complete(messages, model=model)


router = LLMRouter()
