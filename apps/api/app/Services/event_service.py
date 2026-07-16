"""Event service — CRUD with encryption at rest and canvas-type auto-assignment."""
import json
from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Core.patterns import DATE_YMD
from app.dispatch_maps.canvas_type import assign_canvas_type
from app.Models.base import utc_now
from app.Models.event import Event
from app.Pipelines.recurrence import Occurrence, expand_occurrences
from app.Repositories import calendar_repo, event_exception_repo, event_repo
from app.Schemas.base import (
    AttentionClass,
    CanvasEventType,
    EventStatus,
    EventType,
)
from app.Schemas.event import EventCreate, EventOut, EventPatch, EventTitleSuggestion
from app.Services.calendar_service import ensure_default_calendar

DeleteScope = Literal["all", "occurrence", "following"]


class EventError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _naive_utc(value: datetime) -> datetime:
    """DB columns and the recurrence pipeline store/compare naive UTC — FastAPI's
    Query() path can hand back a tz-aware instant even though `UtcDateTime`
    normalizes JSON body fields; normalize defensively at this boundary too.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _decrypt_optional(data_key: bytes, payload: str | None) -> str | None:
    return crypto.decrypt_field(data_key, payload) if payload is not None else None


def to_out(event: Event, data_key: bytes) -> EventOut:
    """Map a stored row (master or plain event) to its own DTO — never an
    occurrence: `master_event_id`/`occurrence_date` are the virtual-instance
    markers and are always None here.
    """
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
        is_recurring=event.is_recurring,
        recurrence_weekdays=json.loads(event.recurrence_weekdays),
        recurrence_end=event.recurrence_end,
        master_event_id=None,
        occurrence_date=None,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _occurrence_out(
    master: Event,
    occurrence: Occurrence,
    title: str,
    description: str | None,
    location: str | None,
) -> EventOut:
    """A virtual occurrence DTO: shares the master's `id` (edit/delete target
    the master row) but carries its own start/end and a distinct identity via
    `master_event_id` + `occurrence_date` — the seam issue #4 (delete this vs
    all-future) hangs off of.
    """
    return EventOut(
        id=master.id,
        calendar_id=master.calendar_id,
        title=title,
        description=description,
        location=location,
        event_type=EventType(master.event_type),
        attention_class=AttentionClass(master.attention_class),
        canvas_event_type=CanvasEventType(master.canvas_event_type or "focus_only"),
        status=EventStatus(master.status),
        start_at=occurrence.start_at,
        end_at=occurrence.end_at,
        is_all_day=master.is_all_day,
        estimated_minutes=master.estimated_minutes,
        actual_minutes=master.actual_minutes,
        residual_of=master.residual_of,
        is_recurring=master.is_recurring,
        recurrence_weekdays=json.loads(master.recurrence_weekdays),
        recurrence_end=master.recurrence_end,
        master_event_id=master.id,
        occurrence_date=occurrence.occurrence_date.isoformat(),
        created_at=master.created_at,
        updated_at=master.updated_at,
    )


def _expand_master(
    master: Event,
    data_key: bytes,
    window_start: datetime,
    window_end: datetime,
    cancelled_dates: frozenset[str],
) -> list[EventOut]:
    """Decrypt the master's sensitive fields once, then emit one EventOut per
    occurrence in the window, skipping any date with a live cancellation
    exception (issue #4, scope="occurrence"). The master row itself is never
    emitted.
    """
    weekdays = frozenset(json.loads(master.recurrence_weekdays))
    occurrences = expand_occurrences(
        master.start_at, master.end_at, weekdays, master.recurrence_end, window_start, window_end
    )
    title = crypto.decrypt_field(data_key, master.title_enc)
    description = _decrypt_optional(data_key, master.description_enc)
    location = _decrypt_optional(data_key, master.location_enc)
    return [
        _occurrence_out(master, occurrence, title, description, location)
        for occurrence in occurrences
        if occurrence.occurrence_date.isoformat() not in cancelled_dates
    ]


async def _reassign_one(session: AsyncSession, event: Event) -> None:
    """Recompute one event's canvas type from its overlapping peers.

    All-day events (a holiday spanning 00:00-24:00) never drive the timed
    overlap classification of the events they happen to span, and never get
    a "spans everything" canvas type themselves — they keep the single-event
    default for their own attention class.
    """
    if event.is_all_day:
        event.canvas_event_type = assign_canvas_type(
            AttentionClass(event.attention_class), frozenset()
        ).value
        return
    peers = await event_repo.list_overlapping(
        session, event.user_id, event.start_at, event.end_at, event.id
    )
    peer_classes = frozenset(
        AttentionClass(peer.attention_class) for peer in peers if not peer.is_all_day
    )
    own_class = AttentionClass(event.attention_class)
    event.canvas_event_type = assign_canvas_type(own_class, peer_classes).value


async def _reassign_range(
    session: AsyncSession, user_id: str, start_at: datetime, end_at: datetime
) -> None:
    """Recompute canvas_event_type for every live event overlapping a range."""
    affected = await event_repo.list_overlapping(session, user_id, start_at, end_at, None)
    for peer in affected:
        await _reassign_one(session, peer)


async def _reassign_canvas_types(session: AsyncSession, event: Event) -> None:
    """Recompute the event's canvas type and its current overlap peers'."""
    await _reassign_one(session, event)
    await _reassign_range(session, event.user_id, event.start_at, event.end_at)


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
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    payload: EventCreate,
    commit: bool = True,
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
        is_recurring=payload.is_recurring,
        recurrence_weekdays=json.dumps(payload.recurrence_weekdays),
        recurrence_end=payload.recurrence_end,
    )
    event_repo.add_event(session, event)
    await session.flush()
    await _reassign_canvas_types(session, event)
    if commit:
        await session.commit()
    return to_out(event, data_key)


async def list_events(
    session: AsyncSession, user_id: str, data_key: bytes, start_at: datetime, end_at: datetime
) -> list[EventOut]:
    """Non-recurring rows pass through as-is; recurring masters expand into
    one EventOut per occurrence inside [start_at, end_at) (sparse, virtual —
    see `_expand_master`). Deterministic for identical inputs.
    """
    window_start, window_end = _naive_utc(start_at), _naive_utc(end_at)
    events = await event_repo.list_for_window(session, user_id, window_start, window_end)
    master_ids = [event.id for event in events if event.is_recurring]
    cancelled = await event_exception_repo.list_cancelled_dates(session, user_id, master_ids)
    out: list[EventOut] = []
    for event in events:
        if event.is_recurring:
            dates = frozenset(cancelled.get(event.id, set()))
            out.extend(_expand_master(event, data_key, window_start, window_end, dates))
        else:
            out.append(to_out(event, data_key))
    return out


async def get_event(
    session: AsyncSession, user_id: str, data_key: bytes, event_id: str
) -> EventOut:
    event = await event_repo.get_event(session, user_id, event_id)
    if event is None:
        raise EventError(404, "event not found")
    return to_out(event, data_key)


_TITLE_SCAN_LIMIT = 500
_TITLE_SUGGESTION_LIMIT = 50


def _event_minutes(event: Event) -> int | None:
    """Best available duration signal: logged actual, else estimate, else the
    scheduled span. All-day events carry no meaningful minutes.
    """
    if event.is_all_day:
        return None
    if event.actual_minutes is not None:
        return event.actual_minutes
    if event.estimated_minutes is not None:
        return event.estimated_minutes
    return max(1, round((event.end_at - event.start_at).total_seconds() / 60))


async def title_suggestions(
    session: AsyncSession, user_id: str, data_key: bytes
) -> list[EventTitleSuggestion]:
    """Group the user's recent events by (decrypted) title into autocomplete
    entries with a count and average duration — the datalist that lets an
    irregular-but-recurring event be re-entered with its learned duration.
    """
    events = await event_repo.list_recent_for_titles(session, user_id, _TITLE_SCAN_LIMIT)
    counts: dict[str, int] = {}
    minute_totals: dict[str, list[int]] = {}
    for event in events:
        title = crypto.decrypt_field(data_key, event.title_enc)
        counts[title] = counts.get(title, 0) + 1
        minutes = _event_minutes(event)
        if minutes is not None:
            minute_totals.setdefault(title, []).append(minutes)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        EventTitleSuggestion(
            title=title,
            occurrence_count=count,
            avg_minutes=_mean_minutes(minute_totals.get(title, [])),
        )
        for title, count in ranked[:_TITLE_SUGGESTION_LIMIT]
    ]


def _mean_minutes(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None


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
    if payload.actual_minutes is not None:
        event.actual_minutes = payload.actual_minutes


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
    old_start, old_end = event.start_at, event.end_at
    if payload.calendar_id is not None:
        event.calendar_id = await _resolve_calendar_id(
            session, user_id, data_key, payload.calendar_id
        )
    _apply_plain_fields(event, payload)
    _apply_encrypted_fields(event, payload, data_key)
    if event.end_at <= event.start_at:
        raise EventError(400, "end_at must be after start_at")
    await session.flush()
    await _reassign_canvas_types(session, event)
    await _reassign_range(session, user_id, old_start, old_end)
    await session.commit()
    return to_out(event, data_key)


def _require_occurrence_date(occurrence_date: str | None, scope: str) -> str:
    if occurrence_date is None or not DATE_YMD.match(occurrence_date):
        raise EventError(400, f"occurrence_date is required for scope={scope}")
    return occurrence_date


async def _delete_all(session: AsyncSession, event: Event, _occurrence_date: str | None) -> None:
    """Soft-delete the master (or a plain, non-recurring event) outright —
    the behavior every scope falls back to.
    """
    old_start, old_end = event.start_at, event.end_at
    event.deleted_at = utc_now()
    await session.flush()
    await _reassign_range(session, event.user_id, old_start, old_end)


async def _delete_occurrence(
    session: AsyncSession, event: Event, occurrence_date: str | None
) -> None:
    """Cancel one occurrence: write a live exception row, master stays put."""
    when = _require_occurrence_date(occurrence_date, "occurrence")
    event_exception_repo.add_exception(session, event.id, event.user_id, when)
    await session.flush()


async def _delete_following(
    session: AsyncSession, event: Event, occurrence_date: str | None
) -> None:
    """Cut the series off before `occurrence_date`: earlier occurrences stay,
    that date and every later one vanish. If the cutoff lands before the
    master's own anchor start (deleting from the first occurrence), there is
    nothing left to keep — soft-delete the whole master instead.
    """
    when = _require_occurrence_date(occurrence_date, "following")
    cutoff = datetime.combine(date.fromisoformat(when), time.min) - timedelta(seconds=1)
    if cutoff < event.start_at:
        await _delete_all(session, event, None)
        return
    event.recurrence_end = cutoff
    await session.flush()


_DELETE_SCOPE_HANDLERS: dict[
    DeleteScope, Callable[[AsyncSession, Event, str | None], Awaitable[None]]
] = {
    "all": _delete_all,
    "occurrence": _delete_occurrence,
    "following": _delete_following,
}


async def delete_event(
    session: AsyncSession,
    user_id: str,
    event_id: str,
    scope: DeleteScope = "all",
    occurrence_date: str | None = None,
) -> None:
    event = await event_repo.get_event(session, user_id, event_id)
    if event is None:
        raise EventError(404, "event not found")
    handler = _DELETE_SCOPE_HANDLERS[scope]
    await handler(session, event, occurrence_date)
    await session.commit()
