"""chore_n_history (healing rows) + schedule_healing_log queries (spec 008).

`chore_n_history` is shared with spec 012 (Chore Entropy) — this repo only
ever writes/reads rows with `reason="healing"`; it doesn't touch rows spec
012 writes with other `reason` values.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.chore_healing import ChoreNHistory, ScheduleHealingLog

_HEALING_REASON = "healing"


def add_n_history(session: AsyncSession, entry: ChoreNHistory) -> ChoreNHistory:
    session.add(entry)
    return entry


def add_healing_log(session: AsyncSession, log: ScheduleHealingLog) -> ScheduleHealingLog:
    session.add(log)
    return log


async def get_latest_healing(session: AsyncSession, chore_id: str) -> ChoreNHistory | None:
    stmt = (
        select(ChoreNHistory)
        .where(ChoreNHistory.chore_id == chore_id, ChoreNHistory.reason == _HEALING_REASON)
        .order_by(ChoreNHistory.recorded_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
