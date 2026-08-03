"""Duration-profile learning (spec 007) — running Welford mean/variance per
event-title label or chore, feeding estimate prefill and `ChoreDefinition.mc_weight`.

The Welford math itself is imported verbatim from `Pipelines/duration_stats`
(pure, already unit-tested there) — this module is the I/O shell around it:
load-or-create a profile row, apply one update, write it back.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.title_hash import hash_title
from app.Models.base import utc_now
from app.Models.chore import ChoreDefinition
from app.Pipelines.duration_stats import WelfordState, welford_update
from app.Repositories import duration_profile_repo
from app.Schemas.duration_profile import DurationProfileOut

_MC_WEIGHT_MIN = 0.25
_MC_WEIGHT_MAX = 4.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


async def record_event_completion(
    session: AsyncSession,
    user_id: str,
    title: str,
    attention_class: str,
    total_minutes: int,
) -> None:
    """Update the running total-minutes stats for this (user, title) label.
    Does not commit — caller's existing transaction owns that.
    """
    label_hash = hash_title(title)
    profile = await duration_profile_repo.upsert(
        session, user_id=user_id, label_hash=label_hash, attention_class=attention_class
    )
    state = WelfordState(
        count=profile.total_sample_count,
        mean=float(profile.total_mean),
        m2=float(profile.total_m2),
    )
    new_state = welford_update(state, float(total_minutes))
    profile.total_sample_count = new_state.count
    profile.total_mean = new_state.mean
    profile.total_m2 = new_state.m2
    profile.last_updated_at = utc_now()
    await session.flush()


async def record_chore_completion(
    session: AsyncSession,
    user_id: str,
    chore: ChoreDefinition,
    total_minutes: int,
) -> float:
    """Update the running total-minutes stats for this chore and recompute
    `mc_weight` from real-vs-estimated, writing it onto both the profile row
    and `chore.mc_weight` (the column the MC scheduler already reads).

    First sample only sets the mean — no ratio to derive a weight from yet,
    so `mc_weight` is left untouched until there's at least one prior sample.
    Does not commit — caller's existing transaction owns that.
    """
    profile = await duration_profile_repo.upsert(session, user_id=user_id, chore_id=chore.id)
    state = WelfordState(
        count=profile.total_sample_count,
        mean=float(profile.total_mean),
        m2=float(profile.total_m2),
    )
    new_state = welford_update(state, float(total_minutes))
    profile.total_sample_count = new_state.count
    profile.total_mean = new_state.mean
    profile.total_m2 = new_state.m2
    profile.last_updated_at = utc_now()

    if new_state.mean > 0:
        weight = _clamp(chore.estimated_minutes / new_state.mean, _MC_WEIGHT_MIN, _MC_WEIGHT_MAX)
        profile.mc_weight = weight
        chore.mc_weight = weight

    await session.flush()
    return float(profile.mc_weight)


async def lookup_by_title(
    session: AsyncSession, user_id: str, title: str
) -> DurationProfileOut | None:
    label_hash = hash_title(title)
    profile = await duration_profile_repo.get_by_label_hash(session, user_id, label_hash)
    if profile is None or profile.total_sample_count == 0:
        return None
    return DurationProfileOut(
        label_hash=profile.label_hash,
        chore_id=profile.chore_id,
        total_sample_count=profile.total_sample_count,
        total_mean=float(profile.total_mean),
        mc_weight=float(profile.mc_weight),
    )
