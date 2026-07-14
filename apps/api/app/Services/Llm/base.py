"""LLM provider seam — routers and services import this protocol only.
This prototype ships exactly one implementation: Ollama.
"""
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


class LlmUnavailableError(Exception):
    """The provider cannot be reached — callers degrade gracefully."""


class LlmProvider(Protocol):
    @property
    def model(self) -> str: ...

    async def chat(self, messages: tuple[ChatMessage, ...]) -> str: ...

    async def health(self) -> tuple[bool, str | None]: ...
