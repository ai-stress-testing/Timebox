"""Chore service — CRUD with encrypted names and next-due bookkeeping."""
import json
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Models.base import utc_now
from app.Models.chore import ChoreDefinition
from app.Pipelines.chore_entropy import days_until_due as compute_days_until_due
from app.Repositories import chore_entropy_repo, chore_healing_repo, chore_repo
from app.Schemas.base import AttentionClass, CalendarColor
from app.Schemas.chore import ChoreCreate, ChoreOut, ChorePatch


class ChoreError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def to_out(session: AsyncSession, chore: ChoreDefinition, data_key: bytes) -> ChoreOut:
    color = CalendarColor(chore.color) if chore.color else None
    entropy = await chore_entropy_repo.get_entropy(session, chore.id)
    recommended_n = entropy.recommended_n if entropy else None
    last_healing = await chore_healing_repo.get_latest_healing(session, chore.id)
    return ChoreOut(
        id=chore.id,
        name=crypto.decrypt_field(data_key, chore.name_enc),
        estimated_minutes=chore.estimated_minutes,
        priority=chore.priority,
        attention_class=AttentionClass(chore.attention_class),
        color=color,
        n_days=chore.n_current,
        n_original=chore.n_original,
        n_current=chore.n_current,
        n_min=chore.n_min,
        n_max=chore.n_max,
        preferred_days=json.loads(chore.preferred_days),
        avoid_days=json.loads(chore.avoid_days),
        preferred_time_start=chore.preferred_time_start,
        preferred_time_end=chore.preferred_time_end,
        is_active=chore.is_active,
        last_completed_at=chore.last_completed_at,
        next_due_at=chore.next_due_at,
        days_until_due=compute_days_until_due(chore.next_due_at, utc_now()),
        recommended_n=recommended_n,
        last_healing_reason=last_healing.reason if last_healing else None,
        last_healing_at=last_healing.recorded_at if last_healing else None,
        created_at=chore.created_at,
        updated_at=chore.updated_at,
    )


async def create_chore(
    session: AsyncSession, user_id: str, data_key: bytes, payload: ChoreCreate
) -> ChoreOut:
    chore = ChoreDefinition(
        user_id=user_id,
        name_enc=crypto.encrypt_field(data_key, payload.name),
        estimated_minutes=payload.estimated_minutes,
        priority=payload.priority,
        attention_class=payload.attention_class.value,
        color=payload.color.value if payload.color else None,
        n_original=payload.n_days,
        n_current=payload.n_days,
        n_min=payload.n_min,
        n_max=payload.n_max,
        preferred_days=json.dumps(payload.preferred_days),
        avoid_days=json.dumps(payload.avoid_days),
        preferred_time_start=payload.preferred_time_start,
        preferred_time_end=payload.preferred_time_end,
        next_due_at=utc_now() + timedelta(days=payload.n_days),
    )
    chore_repo.add_chore(session, chore)
    await session.commit()
    return await to_out(session, chore, data_key)


async def list_chores(session: AsyncSession, user_id: str, data_key: bytes) -> list[ChoreOut]:
    chores = await chore_repo.list_chores(session, user_id)
    return [await to_out(session, chore, data_key) for chore in chores]


def _apply_patch(chore: ChoreDefinition, payload: ChorePatch, data_key: bytes) -> None:
    if payload.name is not None:
        chore.name_enc = crypto.encrypt_field(data_key, payload.name)
    if payload.estimated_minutes is not None:
        chore.estimated_minutes = payload.estimated_minutes
    if payload.priority is not None:
        chore.priority = payload.priority
    if payload.attention_class is not None:
        chore.attention_class = payload.attention_class.value
    if payload.color is not None:
        chore.color = payload.color.value
    if payload.n_days is not None:
        chore.n_current = payload.n_days
    if payload.preferred_days is not None:
        chore.preferred_days = json.dumps(sorted(set(payload.preferred_days)))
    if payload.avoid_days is not None:
        chore.avoid_days = json.dumps(sorted(set(payload.avoid_days)))
    if payload.preferred_time_start is not None:
        chore.preferred_time_start = payload.preferred_time_start
    if payload.preferred_time_end is not None:
        chore.preferred_time_end = payload.preferred_time_end
    if payload.is_active is not None:
        chore.is_active = payload.is_active


async def patch_chore(
    session: AsyncSession, user_id: str, data_key: bytes, chore_id: str, payload: ChorePatch
) -> ChoreOut:
    chore = await chore_repo.get_chore(session, user_id, chore_id)
    if chore is None:
        raise ChoreError(404, "chore not found")
    _apply_patch(chore, payload, data_key)
    if not chore.n_min <= chore.n_current <= chore.n_max:
        raise ChoreError(400, "n_days must lie within [n_min, n_max]")
    await session.commit()
    return await to_out(session, chore, data_key)


async def delete_chore(session: AsyncSession, user_id: str, chore_id: str) -> None:
    chore = await chore_repo.get_chore(session, user_id, chore_id)
    if chore is None:
        raise ChoreError(404, "chore not found")
    chore.deleted_at = utc_now()
    await session.commit()
