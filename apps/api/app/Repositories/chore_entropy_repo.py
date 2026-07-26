"""Chore completion log + entropy stats queries (spec 012)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.chore_entropy import ChoreCompletion, ChoreEntropy


def add_completion(session: AsyncSession, completion: ChoreCompletion) -> ChoreCompletion:
    session.add(completion)
    return completion


async def get_entropy(session: AsyncSession, chore_id: str) -> ChoreEntropy | None:
    stmt = select(ChoreEntropy).where(
        ChoreEntropy.chore_id == chore_id, ChoreEntropy.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_entropy(
    session: AsyncSession,
    chore_id: str,
    decay_days_mean: float,
    decay_days_m2: float,
    decay_sample_count: int,
    recommended_n: int | None,
    last_computed_at,
) -> ChoreEntropy:
    entropy = await get_entropy(session, chore_id)
    if entropy is None:
        entropy = ChoreEntropy(chore_id=chore_id)
        session.add(entropy)
    entropy.decay_days_mean = decay_days_mean
    entropy.decay_days_m2 = decay_days_m2
    entropy.decay_sample_count = decay_sample_count
    entropy.recommended_n = recommended_n
    entropy.last_computed_at = last_computed_at
    return entropy
