"""Canvas service — CRUD for directly-created timers/stopwatches (spec 010).

`canvas_items` is a first-class entity, not a snapshot/view of `events`:
most items never touch the events table. Optional event linkage
(`create_timer`'s `event_id`) validates ownership and snapshots
`attention_class`/`canvas_event_type` at link time — a copy, not a live
join, so an unrelated edit to the linked event later never reshuffles this
item's canvas placement (see spec 010's note). `delete_item` never mutates
the linked event, if any — same "canvas never mutates the calendar"
invariant the rest of this backend follows for todos/pomodoro.

`move_item` (writing `canvas_position_history`) is folded into `edit_item`
rather than exposed as its own function/endpoint: the API surface this spec
defines has a single `PATCH /canvas/items/{id}` for title/duration/position
edits, so a drag-end simply includes r/theta in that same patch — see the
deviations note in specs/010-radial-canvas/plan.md.
"""
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Models.base import utc_now
from app.Models.canvas import CanvasAlarm, CanvasItem, CanvasPositionHistory
from app.Pipelines.canvas_timer import is_timer_complete, live_elapsed
from app.Repositories import canvas_repo, event_repo
from app.Schemas.base import AttentionClass
from app.Schemas.canvas import (
    CanvasAlarmCreate,
    CanvasAlarmOut,
    CanvasAlarmPatch,
    CanvasItemCreate,
    CanvasItemOut,
    CanvasItemPatch,
)


class CanvasError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _sync_completion(item: CanvasItem, now: datetime) -> None:
    """Lazily flip a running timer to "completed" once its countdown target
    has elapsed — checked on every read/transition, never a background
    poller (NASA rule 2: no hidden control flow off the request path).
    """
    if item.status != "running":
        return
    elapsed = live_elapsed(item.accumulated_seconds, item.started_at, item.status, now)
    if is_timer_complete(item.mode, item.duration_seconds, elapsed):
        item.status = "completed"
        item.accumulated_seconds = (
            item.duration_seconds if item.duration_seconds is not None else elapsed
        )
        item.started_at = None


def _to_out(item: CanvasItem, data_key: bytes, now: datetime) -> CanvasItemOut:
    elapsed = live_elapsed(item.accumulated_seconds, item.started_at, item.status, now)
    return CanvasItemOut(
        id=item.id,
        title=crypto.decrypt_field(data_key, item.title_enc),
        mode=item.mode,
        duration_seconds=item.duration_seconds,
        accumulated_seconds=item.accumulated_seconds,
        elapsed_seconds=elapsed,
        started_at=item.started_at,
        status=item.status,
        event_id=item.event_id,
        attention_class=AttentionClass(item.attention_class),
        canvas_event_type=item.canvas_event_type,
        r=float(item.r),
        theta=float(item.theta),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _alarm_out(alarm: CanvasAlarm) -> CanvasAlarmOut:
    return CanvasAlarmOut(
        id=alarm.id,
        canvas_item_id=alarm.canvas_item_id,
        alarm_class=alarm.alarm_class,
        label=alarm.label,
        offset_seconds=alarm.offset_seconds,
        fires_at=alarm.fires_at,
        status=alarm.status,
        fired_at=alarm.fired_at,
        acknowledged_at=alarm.acknowledged_at,
        snoozed_until=alarm.snoozed_until,
    )


async def _resolve_event_link(
    session: AsyncSession, user_id: str, event_id: str | None
) -> tuple[str | None, str | None]:
    """Validate ownership and snapshot (attention_class, canvas_event_type)
    from the linked event, if any. `(None, None)` means "no link — fall
    back to the request/default values instead".
    """
    if event_id is None:
        return None, None
    event = await event_repo.get_event(session, user_id, event_id)
    if event is None:
        raise CanvasError(404, "linked event not found")
    return event.attention_class, event.canvas_event_type


async def _get_or_404(session: AsyncSession, user_id: str, item_id: str) -> CanvasItem:
    item = await canvas_repo.get_item(session, user_id, item_id)
    if item is None:
        raise CanvasError(404, "canvas item not found")
    return item


async def create_timer(
    session: AsyncSession, user_id: str, data_key: bytes, payload: CanvasItemCreate
) -> CanvasItemOut:
    snapshot_attention, snapshot_canvas_type = await _resolve_event_link(
        session, user_id, payload.event_id
    )
    item = CanvasItem(
        user_id=user_id,
        title_enc=crypto.encrypt_field(data_key, payload.title),
        mode=payload.mode,
        duration_seconds=payload.duration_seconds,
        accumulated_seconds=0,
        started_at=None,
        status="paused",
        event_id=payload.event_id,
        attention_class=snapshot_attention or payload.attention_class.value,
        canvas_event_type=snapshot_canvas_type,
        r=payload.r,
        theta=payload.theta,
    )
    canvas_repo.add_item(session, item)
    await session.commit()
    return _to_out(item, data_key, utc_now())


async def list_items(session: AsyncSession, user_id: str, data_key: bytes) -> list[CanvasItemOut]:
    items = await canvas_repo.list_for_user(session, user_id)
    now = utc_now()
    changed = False
    for item in items:
        before_status = item.status
        _sync_completion(item, now)
        changed = changed or item.status != before_status
    if changed:
        await session.commit()
    return [_to_out(item, data_key, now) for item in items]


async def get_item(
    session: AsyncSession, user_id: str, data_key: bytes, item_id: str
) -> CanvasItemOut:
    item = await _get_or_404(session, user_id, item_id)
    now = utc_now()
    before_status = item.status
    _sync_completion(item, now)
    if item.status != before_status:
        await session.commit()
    return _to_out(item, data_key, now)


async def start_item(
    session: AsyncSession, user_id: str, data_key: bytes, item_id: str
) -> CanvasItemOut:
    item = await _get_or_404(session, user_id, item_id)
    now = utc_now()
    _sync_completion(item, now)
    if item.status == "completed":
        raise CanvasError(409, "cannot start a completed timer")
    if item.status != "running":
        item.status = "running"
        item.started_at = now
    await session.commit()
    return _to_out(item, data_key, now)


async def pause_item(
    session: AsyncSession, user_id: str, data_key: bytes, item_id: str
) -> CanvasItemOut:
    item = await _get_or_404(session, user_id, item_id)
    now = utc_now()
    _sync_completion(item, now)
    if item.status == "running":
        item.accumulated_seconds = live_elapsed(
            item.accumulated_seconds, item.started_at, item.status, now
        )
        item.status = "paused"
        item.started_at = None
    await session.commit()
    return _to_out(item, data_key, now)


async def reset_item(
    session: AsyncSession, user_id: str, data_key: bytes, item_id: str
) -> CanvasItemOut:
    item = await _get_or_404(session, user_id, item_id)
    item.status = "paused"
    item.accumulated_seconds = 0
    item.started_at = None
    await session.commit()
    return _to_out(item, data_key, utc_now())


def _record_move(item: CanvasItem, r: float | None, theta: float | None) -> CanvasPositionHistory:
    r_before, theta_before = float(item.r), float(item.theta)
    if r is not None:
        item.r = r
    if theta is not None:
        item.theta = theta
    return CanvasPositionHistory(
        canvas_item_id=item.id,
        user_id=item.user_id,
        r_before=r_before,
        theta_before=theta_before,
        r_after=float(item.r),
        theta_after=float(item.theta),
    )


async def edit_item(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    item_id: str,
    payload: CanvasItemPatch,
) -> CanvasItemOut:
    item = await _get_or_404(session, user_id, item_id)
    if payload.title is not None:
        item.title_enc = crypto.encrypt_field(data_key, payload.title)
    if payload.duration_seconds is not None:
        item.duration_seconds = payload.duration_seconds
    if payload.r is not None or payload.theta is not None:
        history = _record_move(item, payload.r, payload.theta)
        canvas_repo.add_position_history(session, history)
    now = utc_now()
    _sync_completion(item, now)
    await session.commit()
    return _to_out(item, data_key, now)


async def delete_item(session: AsyncSession, user_id: str, item_id: str) -> None:
    """Soft delete. Never touches `event_id`'s row — the linked event, if
    any, is left completely untouched."""
    item = await _get_or_404(session, user_id, item_id)
    item.deleted_at = utc_now()
    await session.commit()


async def create_alarm(
    session: AsyncSession, user_id: str, item_id: str, payload: CanvasAlarmCreate
) -> CanvasAlarmOut:
    item = await _get_or_404(session, user_id, item_id)
    anchor = item.started_at or utc_now()
    fires_at = anchor + timedelta(seconds=payload.offset_seconds)
    alarm = CanvasAlarm(
        canvas_item_id=item.id,
        user_id=user_id,
        alarm_class=payload.alarm_class,
        label=payload.label,
        offset_seconds=payload.offset_seconds,
        fires_at=fires_at,
        status="pending",
    )
    canvas_repo.add_alarm(session, alarm)
    await session.commit()
    return _alarm_out(alarm)


async def patch_alarm(
    session: AsyncSession, user_id: str, alarm_id: str, payload: CanvasAlarmPatch
) -> CanvasAlarmOut:
    alarm = await canvas_repo.get_alarm(session, user_id, alarm_id)
    if alarm is None:
        raise CanvasError(404, "alarm not found")
    now = utc_now()
    if payload.status is not None:
        alarm.status = payload.status
        if payload.status == "acknowledged":
            alarm.acknowledged_at = now
        elif payload.status == "fired":
            alarm.fired_at = now
    if payload.snoozed_until is not None:
        alarm.snoozed_until = payload.snoozed_until
        alarm.status = "snoozed"
    await session.commit()
    return _alarm_out(alarm)
