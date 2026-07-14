"""Session store seam. Prototype: in-memory TTL map. Production swap: Redis
implementation of the same interface (`sess:{user_id}:{token}` keys, TTL 12h).
The data key lives only inside a session entry — never persisted.
"""
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Protocol

_MAX_SESSIONS = 64


@dataclass(frozen=True)
class SessionEntry:
    token: str
    user_id: str
    data_key: bytes
    expires_at: datetime
    hard_expires_at: datetime


class SessionStore(Protocol):
    def create(self, user_id: str, data_key: bytes) -> SessionEntry: ...
    def resolve(self, token: str) -> SessionEntry | None: ...
    def revoke(self, token: str) -> None: ...
    def revoke_all(self) -> None: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemorySessionStore:
    def __init__(self, ttl_hours: int, max_lifetime_hours: int = 24) -> None:
        self._ttl = timedelta(hours=ttl_hours)
        self._max_lifetime = timedelta(hours=max_lifetime_hours)
        self._entries: dict[str, SessionEntry] = {}

    def create(self, user_id: str, data_key: bytes) -> SessionEntry:
        self._prune()
        token = secrets.token_urlsafe(32)
        hard_deadline = _now() + self._max_lifetime
        expires_at = min(_now() + self._ttl, hard_deadline)
        entry = SessionEntry(token, user_id, data_key, expires_at, hard_deadline)
        self._entries = {**self._entries, token: entry}
        return entry

    def resolve(self, token: str) -> SessionEntry | None:
        entry = self._entries.get(token)
        is_live = entry is not None and entry.expires_at > _now()
        if entry is not None and not is_live:
            self.revoke(token)
        if not is_live or entry is None:
            return None
        # Sliding TTL, but never past the absolute lifetime: background
        # polling (e.g. the AI health check) must not keep a leaked token —
        # and the in-memory data key — alive forever.
        extended = min(_now() + self._ttl, entry.hard_expires_at)
        refreshed = replace(entry, expires_at=extended)
        self._entries = {**self._entries, token: refreshed}
        return refreshed

    def revoke(self, token: str) -> None:
        self._entries = {k: v for k, v in self._entries.items() if k != token}

    def revoke_all(self) -> None:
        self._entries = {}

    def _prune(self) -> None:
        now = _now()
        live = {k: v for k, v in self._entries.items() if v.expires_at > now}
        newest = sorted(live.items(), key=lambda kv: kv[1].expires_at)[-_MAX_SESSIONS:]
        self._entries = dict(newest)
