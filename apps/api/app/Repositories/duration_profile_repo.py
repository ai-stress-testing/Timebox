"""Duration-profile queries (spec 007) — one row per (user, label_hash) or
(user, chore_id); live rows only (soft delete).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.duration_profile import DurationProfile


async def get_by_label_hash(
    session: AsyncSession, user_id: str, label_hash: str
) -> DurationProfile | None:
    stmt = select(DurationProfile).where(
        DurationProfile.user_id == user_id,
        DurationProfile.label_hash == label_hash,
        DurationProfile.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_chore_id(
    session: AsyncSession, user_id: str, chore_id: str
) -> DurationProfile | None:
    stmt = select(DurationProfile).where(
        DurationProfile.user_id == user_id,
        DurationProfile.chore_id == chore_id,
        DurationProfile.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def add_profile(session: AsyncSession, profile: DurationProfile) -> DurationProfile:
    session.add(profile)
    return profile


async def upsert(
    session: AsyncSession,
    *,
    user_id: str,
    label_hash: str | None = None,
    chore_id: str | None = None,
    attention_class: str | None = None,
) -> DurationProfile:
    """Load the existing profile row for this (user, label_hash|chore_id), or
    create a fresh one if none exists yet. Does not persist stat fields —
    callers apply their own `welford_update` result before saving.
    """
    profile: DurationProfile | None = None
    if label_hash is not None:
        profile = await get_by_label_hash(session, user_id, label_hash)
    elif chore_id is not None:
        profile = await get_by_chore_id(session, user_id, chore_id)
    else:
        raise ValueError("upsert requires label_hash or chore_id")

    if profile is None:
        # Explicit zero/one defaults rather than relying on the mapped_column
        # `default=` — those only materialize at flush/INSERT time, but the
        # caller reads these fields off the in-memory object before flushing.
        profile = DurationProfile(
            user_id=user_id,
            label_hash=label_hash,
            chore_id=chore_id,
            attention_class=attention_class,
            total_sample_count=0,
            total_mean=0,
            total_m2=0,
            meaningful_sample_count=0,
            meaningful_mean=0,
            meaningful_m2=0,
            mc_weight=1.0,
        )
        add_profile(session, profile)
    elif attention_class is not None:
        profile.attention_class = attention_class
    return profile
