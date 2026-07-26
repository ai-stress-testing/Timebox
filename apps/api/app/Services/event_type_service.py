"""Event-type service — 7-preset bootstrap (mirrors `ensure_default_calendar`)
plus custom-type CRUD. `valid_keys` backs the dynamic `event_type` validation
in `event_service` (replacing the old static enum)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Core.patterns import SLUG_NON_ALNUM
from app.Models.base import utc_now
from app.Models.event_type import EventType
from app.Repositories import event_type_repo
from app.Schemas.base import CalendarColor
from app.Schemas.event import EventTypeCreate, EventTypePatch, EventTypeSummary

# (key, color) in seed/sort order — labels are the capitalized key.
_PRESETS: tuple[tuple[str, CalendarColor], ...] = (
    ("meeting", CalendarColor.sky),
    ("task", CalendarColor.violet),
    ("personal", CalendarColor.emerald),
    ("chore", CalendarColor.amber),
    ("homework", CalendarColor.rose),
    ("passive", CalendarColor.slate),
    ("physical", CalendarColor.orange),
)

_SLUG_MAX_ATTEMPTS = 50
# Leaves room for a "-NN" dedupe suffix under the `event_types.key` /
# `events.event_type` column width (64) without truncation.
_SLUG_BASE_MAX_LEN = 56


class EventTypeError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _to_out(event_type: EventType, data_key: bytes) -> EventTypeSummary:
    return EventTypeSummary(
        id=event_type.id,
        key=event_type.key,
        label=crypto.decrypt_field(data_key, event_type.label_enc),
        color=CalendarColor(event_type.color),
        is_preset=event_type.is_preset,
        is_active=event_type.is_active,
        sort_order=event_type.sort_order,
    )


async def ensure_seeded(session: AsyncSession, user_id: str, data_key: bytes) -> None:
    """Seed the 7 presets exactly once per user — a no-op once any row exists."""
    existing_count = await event_type_repo.count_for_user(session, user_id)
    if existing_count > 0:
        return
    for sort_order, (key, color) in enumerate(_PRESETS):
        event_type = EventType(
            user_id=user_id,
            key=key,
            label_enc=crypto.encrypt_field(data_key, key.capitalize()),
            color=color.value,
            is_preset=True,
            is_active=True,
            sort_order=sort_order,
        )
        event_type_repo.add_event_type(session, event_type)
    # Flush, not commit: when called inside create_event(commit=False) (the
    # apply_run path), an inner commit would break that caller's single-commit
    # atomicity. Callers that need durability commit themselves.
    await session.flush()


async def list_types(
    session: AsyncSession, user_id: str, data_key: bytes
) -> list[EventTypeSummary]:
    await ensure_seeded(session, user_id, data_key)
    rows = await event_type_repo.list_active(session, user_id)
    # This GET seeds presets on first access — persist that seed.
    await session.commit()
    return [_to_out(row, data_key) for row in rows]


def _slugify(label: str) -> str:
    slug = SLUG_NON_ALNUM.sub("-", label.strip().lower()).strip("-")
    slug = slug[:_SLUG_BASE_MAX_LEN].strip("-")
    return slug or "type"


async def _unique_key(session: AsyncSession, user_id: str, label: str) -> str:
    base_slug = _slugify(label)
    candidate = base_slug
    for attempt in range(1, _SLUG_MAX_ATTEMPTS + 1):
        existing = await event_type_repo.get_by_key(session, user_id, candidate)
        if existing is None:
            return candidate
        candidate = f"{base_slug}-{attempt + 1}"
    raise EventTypeError(409, "could not derive a unique key for this label")


async def create_type(
    session: AsyncSession, user_id: str, data_key: bytes, payload: EventTypeCreate
) -> EventTypeSummary:
    await ensure_seeded(session, user_id, data_key)
    key = await _unique_key(session, user_id, payload.label)
    sort_order = await event_type_repo.count_for_user(session, user_id)
    event_type = EventType(
        user_id=user_id,
        key=key,
        label_enc=crypto.encrypt_field(data_key, payload.label),
        color=payload.color.value,
        is_preset=False,
        is_active=True,
        sort_order=sort_order,
    )
    event_type_repo.add_event_type(session, event_type)
    await session.commit()
    return _to_out(event_type, data_key)


def _apply_patch(event_type: EventType, payload: EventTypePatch, data_key: bytes) -> None:
    if payload.label is not None:
        event_type.label_enc = crypto.encrypt_field(data_key, payload.label)
    if payload.color is not None:
        event_type.color = payload.color.value
    if payload.is_active is not None:
        event_type.is_active = payload.is_active
    if payload.sort_order is not None:
        event_type.sort_order = payload.sort_order


async def patch_type(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    event_type_id: str,
    payload: EventTypePatch,
) -> EventTypeSummary:
    event_type = await event_type_repo.get_event_type(session, user_id, event_type_id)
    if event_type is None:
        raise EventTypeError(404, "event type not found")
    _apply_patch(event_type, payload, data_key)
    await session.commit()
    return _to_out(event_type, data_key)


async def delete_type(session: AsyncSession, user_id: str, event_type_id: str) -> None:
    event_type = await event_type_repo.get_event_type(session, user_id, event_type_id)
    if event_type is None:
        raise EventTypeError(404, "event type not found")
    if event_type.is_preset:
        raise EventTypeError(409, "preset event types cannot be deleted")
    event_type.deleted_at = utc_now()
    await session.commit()


async def valid_keys(session: AsyncSession, user_id: str) -> set[str]:
    rows = await event_type_repo.list_active(session, user_id)
    return {row.key for row in rows if row.is_active}
