"""14-day hard purge — the pg_cron contract implemented in-app for the prototype.
Fact of deletion is kept in purge_audit; the data itself is gone.
"""
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.config import settings
from app.Core.ids import uuid7
from app.Core.logging import get_logger
from app.Models import (
    AiSession,
    Calendar,
    ChoreDefinition,
    ChoreOccurrence,
    Event,
    PomodoroSession,
    PurgeAudit,
    ResidualPrompt,
    ScheduleRun,
    TaskResidual,
)
from app.Models.base import utc_now

_log = get_logger(__name__)

_PURGEABLE_MODELS = (
    Event,
    Calendar,
    ChoreDefinition,
    ScheduleRun,
    ChoreOccurrence,
    PomodoroSession,
    ResidualPrompt,
    TaskResidual,
    AiSession,
)


async def _purge_model(session: AsyncSession, model: type, cutoff) -> int:  # type: ignore[no-untyped-def]
    stmt = select(model.id, model.deleted_at).where(
        model.deleted_at.is_not(None), model.deleted_at < cutoff
    )
    rows = (await session.execute(stmt)).all()
    now_iso = utc_now().isoformat()
    for record_id, deleted_at in rows:
        session.add(
            PurgeAudit(
                id=uuid7(),
                table_name=model.__tablename__,
                record_id=record_id,
                deleted_at=deleted_at.isoformat(),
                purged_at=now_iso,
            )
        )
    if rows:
        await session.execute(delete(model).where(model.id.in_([r[0] for r in rows])))
    return len(rows)


async def run_purge(session: AsyncSession) -> int:
    cutoff = utc_now() - timedelta(days=settings.purge_after_days)
    total = 0
    for model in _PURGEABLE_MODELS:
        total += await _purge_model(session, model, cutoff)
    await session.commit()
    if total:
        _log.info(f"hard purge removed {total} records past {settings.purge_after_days}d window")
    return total
