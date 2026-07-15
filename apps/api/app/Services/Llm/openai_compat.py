"""OpenAI-compatible chat-completions provider — any local endpoint that speaks
the `/v1/chat/completions` schema: LM Studio, Ollama's own `/v1` shim, etc.
"""
import httpx

from app.Services.Llm.base import ChatMessage, LlmUnavailableError


class OpenAiCompatProvider:
    """Built per-request via the factory — settings are user-chosen, not fixed at boot."""

    def __init__(
        self, base_url: str, model: str, timeout_seconds: float, api_key: str | None = None
    ) -> None:
        self._model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout_seconds, headers=headers
        )

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
        }
        try:
            response = await self._client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmUnavailableError(f"openai-compat unreachable: {type(exc).__name__}") from exc
        body = response.json()
        choices = body.get("choices") or [{}]
        message = choices[0].get("message", {}) if choices else {}
        return str(message.get("content", ""))

    async def health(self) -> tuple[bool, str | None]:
        try:
            response = await self._client.get("/v1/models", timeout=3.0)
            response.raise_for_status()
            return True, None
        except httpx.HTTPError as exc:
            return False, f"openai-compat unreachable: {type(exc).__name__}"

    async def close(self) -> None:
        await self._client.aclose()
