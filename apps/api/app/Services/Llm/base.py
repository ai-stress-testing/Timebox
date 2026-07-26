"""LLM provider seam — routers and services import this protocol only.
Local runtimes only (constitution Article I): Ollama native, or any
OpenAI-compatible local endpoint (LM Studio, Ollama's /v1, etc.).
"""
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user"]

ProviderKind = Literal["ollama", "openai_compat"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


class LlmUnavailableError(Exception):
    """The provider cannot be reached — callers degrade gracefully."""


class LlmProvider(Protocol):
    @property
    def model(self) -> str: ...

    @property
    def base_url(self) -> str: ...

    async def chat(self, messages: tuple[ChatMessage, ...]) -> str: ...

    async def health(self) -> tuple[bool, str | None]: ...

    async def close(self) -> None: ...
