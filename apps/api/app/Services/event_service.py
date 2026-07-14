"""Event service — CRUD with encryption at rest and canvas-type auto-assignment."""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.dispatch_maps.canvas_type import assign_canvas_type
from app.Models.base import utc_now
from app.Models.event import Event
from app.Repositories import calendar_repo, event_repo
from app.Schemas.base import (
    AttentionClass,
    CanvasEventType,
    EventStatus,
    EventType,
)
from app.Schemas.event import EventCreate, EventOut, EventPatch
from app.Services.calendar_service import ensure_default_calendar


class EventError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _decrypt_optional(data_key: bytes, payload: str | None) -> str | None:
    return crypto.decrypt_field(data_key, payload) if payload is not None else None


def to_out(event: Event, data_key: bytes) -> EventOut:
    return EventOut(
        id=event.id,
        calendar_id=event.calendar_id,
        title=crypto.decrypt_field(data_key, event.title_enc),
        description=_decrypt_optional(data_key, event.description_enc),
        location=_decrypt_optional(data_key, event.location_enc),
        event_type=EventType(event.event_type),
        attention_class=AttentionClass(event.attention_class),
        canvas_event_type=CanvasEventType(event.canvas_event_type or "focus_only"),
        status=EventStatus(event.status),
        start_at=event.start_at,
        end_at=event.end_at,
        is_all_day=event.is_all_day,
        estimated_minutes=event.estimated_minutes,
        actual_minutes=event.actual_minutes,
        residual_of=event.residual_of,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


async def _reassign_canvas_types(session: AsyncSession, event: Event) -> None:
    """Recompute canvas_event_type for the event and everything it overlaps."""
    overlapping = await event_repo.list_overlapping(
        session, event.user_id, event.start_at, event.end_at, event.id
    )
    peer_classes = frozenset(AttentionClass(peer.attention_class) for peer in overlapping)
    own_class = AttentionClass(event.attention_class)
    event.canvas_event_type = assign_canvas_type(own_class, peer_classes).value
    for peer in overlapping:
        peer_peers = await event_repo.list_overlapping(
            session, peer.user_id, peer.start_at, peer.end_at, peer.id
        )
        classes = frozenset(AttentionClass(p.attention_class) for p in peer_peers)
        peer.canvas_event_type = assign_canvas_type(
            AttentionClass(peer.attention_class), classes
        ).value


async def _resolve_calendar_id(
    session: AsyncSession, user_id: str, data_key: bytes, calendar_id: str | None
) -> str:
    if calendar_id is None:
        default = await ensure_default_calendar(session, user_id, data_key)
        return default.id
    calendar = await calendar_repo.get_calendar(session, user_id, calendar_id)
    if calendar is None:
        raise EventError(404, "calendar not found")
    return calendar.id


async def create_event(
    session: AsyncSession, user_id: str, data_key: bytes, payload: EventCreate
) -> EventOut:
    calendar_id = await _resolve_calendar_id(session, user_id, data_key, payload.calendar_id)
    event = Event(
        calendar_id=calendar_id,
        user_id=user_id,
        event_type=payload.event_type.value,
        attention_class=payload.attention_class.value,
        title_enc=crypto.encrypt_field(data_key, payload.title),
        description_enc=(
            crypto.encrypt_field(data_key, payload.description) if payload.description else None
        ),
        location_enc=(
            crypto.encrypt_field(data_key, payload.location) if payload.location else None
        ),
        start_at=payload.start_at,
        end_at=payload.end_at,
        is_all_day=payload.is_all_day,
        estimated_minutes=payload.estimated_minutes,
    )
    event_repo.add_event(session, event)
    await session.flush()
    await _reassign_canvas_types(session, event)
    await session.commit()
    return to_out(event, data_key)


async def list_events(
    session: AsyncSession, user_id: str, data_key: bytes, start_at: datetime, end_at: datetime
) -> list[EventOut]:
    events = await event_repo.list_in_range(session, user_id, start_at, end_at)
    return [to_out(event, data_key) for event in events]


async def get_event(
    session: AsyncSession, user_id: str, data_key: bytes, event_id: str
) -> EventOut:
    event = await event_repo.get_event(session, user_id, event_id)
    if event is None:
        raise EventError(404, "event not found")
    return to_out(event, data_key)


def _apply_plain_fields(event: Event, payload: EventPatch) -> None:
    if payload.event_type is not None:
        event.event_type = payload.event_type.value
    if payload.attention_class is not None:
        event.attention_class = payload.attention_class.value
    if payload.status is not None:
        event.status = payload.status.value
    if payload.start_at is not None:
        event.start_at = payload.start_at
    if payload.end_at is not None:
        event.end_at = payload.end_at
    if payload.is_all_day is not None:
        event.is_all_day = payload.is_all_day
    if payload.estimated_minutes is not None:
        event.estimated_minutes = payload.estimated_minutes


def _apply_encrypted_fields(event: Event, payload: EventPatch, data_key: bytes) -> None:
    if payload.title is not None:
        event.title_enc = crypto.encrypt_field(data_key, payload.title)
    if payload.description is not None:
        event.description_enc = crypto.encrypt_field(data_key, payload.description)
    if payload.location is not None:
        event.location_enc = crypto.encrypt_field(data_key, payload.location)


async def patch_event(
    session: AsyncSession, user_id: str, data_key: bytes, event_id: str, payload: EventPatch
) -> EventOut:
    event = await event_repo.get_event(session, user_id, event_id)
    if event is None:
        raise EventError(404, "event not found")
    if payload.calendar_id is not None:
        event.calendar_id = await _resolve_calendar_id(
            session, user_id, data_key, payload.calendar_id
        )
    _apply_plain_fields(event, payload)
    _apply_encrypted_fields(event, payload, data_key)
    if event.end_at <= event.start_at:
        raise EventError(400, "end_at must be after start_at")
    await _reassign_canvas_types(session, event)
    await session.commit()
    return to_out(event, data_key)


async def delete_event(session: AsyncSession, user_id: str, event_id: str) -> None:
    event = await event_repo.get_event(session, user_id, event_id)
    if event is None:
        raise EventError(404, "event not found")
    event.deleted_at = utc_now()
    await session.commit()
