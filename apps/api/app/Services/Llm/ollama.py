"""Ollama provider — local daemon, config-driven base URL + model, JSON mode."""
import httpx

from app.Core.config import settings
from app.Services.Llm.base import ChatMessage, LlmUnavailableError


class OllamaProvider:
    """Singleton created at boot (NASA rule 3) — one AsyncClient for the process."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self._model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return str(self._client.base_url)

    async def chat(self, messages: tuple[ChatMessage, ...]) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "format": "json",
        }
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmUnavailableError(f"ollama unreachable: {type(exc).__name__}") from exc
        body = response.json()
        return str(body.get("message", {}).get("content", ""))

    async def health(self) -> tuple[bool, str | None]:
        try:
            response = await self._client.get("/api/tags", timeout=3.0)
            response.raise_for_status()
            return True, None
        except httpx.HTTPError as exc:
            return False, f"ollama unreachable: {type(exc).__name__}"

    async def close(self) -> None:
        await self._client.aclose()


def build_default_provider() -> OllamaProvider:
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
