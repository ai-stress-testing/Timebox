"""Ollama provider — local daemon, config-driven base URL with an automatic
Docker-internal fallback when the primary is unreachable.
"""
import httpx

from app.Core.config import settings
from app.Core.logging import get_logger
from app.Services.Llm.base import ChatMessage, LlmUnavailableError

_log = get_logger(__name__)


class OllamaProvider:
    """Singleton created at boot (NASA rule 3) — one AsyncClient for the process.

    Every call tries `base_url` first. If that fails at the transport level
    (DNS/refused/timeout — exactly what "`host.docker.internal` doesn't
    resolve" or "the sidecar isn't up yet" look like, not a non-2xx response)
    and a distinct `fallback_base_url` is configured, the call is retried once
    against it. The retry is stateless — every call prefers the primary again
    — so a host Ollama that starts after the container did is picked back up
    automatically, matching docker-compose.yml's `ollama` sidecar as a
    fallback rather than a one-time mode switch the user has to opt into.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        fallback_base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        normalized_fallback = fallback_base_url.rstrip("/") if fallback_base_url else None
        self._fallback_base_url = (
            normalized_fallback if normalized_fallback != self._base_url else None
        )
        self._active_base_url = self._base_url
        self._client = httpx.AsyncClient(timeout=timeout_seconds, transport=transport)

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        """The URL that actually served the most recent request."""
        return self._active_base_url

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        try:
            response = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
            self._active_base_url = self._base_url
            return response
        except httpx.TransportError:
            if self._fallback_base_url is None:
                raise
            _log.info(f"ollama primary unreachable, trying fallback {self._fallback_base_url}")
            response = await self._client.request(
                method, f"{self._fallback_base_url}{path}", **kwargs
            )
            self._active_base_url = self._fallback_base_url
            return response

    async def chat(self, messages: tuple[ChatMessage, ...]) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "format": "json",
        }
        try:
            response = await self._request("POST", "/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmUnavailableError(f"ollama unreachable: {type(exc).__name__}") from exc
        body = response.json()
        return str(body.get("message", {}).get("content", ""))

    async def health(self) -> tuple[bool, str | None]:
        try:
            response = await self._request("GET", "/api/tags", timeout=3.0)
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
        fallback_base_url=settings.ollama_fallback_base_url,
    )
