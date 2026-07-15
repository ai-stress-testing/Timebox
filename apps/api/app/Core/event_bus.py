"""Event bus seam. Prototype: in-process async pub/sub. Production swap:
Redis Streams implementation of the same interface (constitution Article II).
"""
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

Handler = Callable[[dict[str, Any]], Awaitable[None]]

_MAX_HANDLERS_PER_STREAM = 16


class EventBus(Protocol):
    def subscribe(self, stream: str, handler: Handler) -> None: ...
    async def publish(self, stream: str, payload: dict[str, Any]) -> None: ...


class InProcessEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, tuple[Handler, ...]] = {}

    def subscribe(self, stream: str, handler: Handler) -> None:
        current = self._handlers.get(stream, ())
        if len(current) >= _MAX_HANDLERS_PER_STREAM:
            raise RuntimeError(f"handler limit reached for stream {stream}")
        self._handlers = {**self._handlers, stream: (*current, handler)}

    async def publish(self, stream: str, payload: dict[str, Any]) -> None:
        for handler in self._handlers.get(stream, ()):
            await handler(payload)


event_bus = InProcessEventBus()
