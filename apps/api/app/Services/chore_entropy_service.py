"""Chore completion + decay-rate learning (spec 012).

Logs a completion, updates the chore's Welford decay stats (skipped for a
chore's very first completion — there's no prior `last_completed_at` to
diff against), caches a fresh `recommended_n`, and refreshes the chore's own
`last_completed_at`/`next_due_at` the same way `create_chore` seeds them.
"""
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.base import utc_now
from app.Models.chore_entropy import ChoreCompletion
from app.Pipelines.chore_entropy import recommended_split
from app.Pipelines.duration_stats import WelfordState, welford_update
from app.Repositories import chore_entropy_repo, chore_repo
from app.Schemas.chore import ChoreOut
from app.Services import chore_service
from app.Services.chore_service import ChoreError


async def record_completion(
    session: AsyncSession,
    user_id: str,
    data_key: bytes,
    chore_id: str,
    completed_at: datetime | None = None,
) -> ChoreOut:
    chore = await chore_repo.get_chore(session, user_id, chore_id)
    if chore is None:
        raise ChoreError(404, "chore not found")

    when = completed_at or utc_now()
    previous = chore.last_completed_at

    days_since_previous: float | None = None
    if previous is not None:
        days_since_previous = (when - previous).total_seconds() / 86400

    chore_entropy_repo.add_completion(
        session,
        ChoreCompletion(
            chore_id=chore.id,
            user_id=user_id,
            completed_at=when,
            days_since_previous=days_since_previous,
        ),
    )

    # First-ever completion: nothing to diff against yet, so the Welford
    # update (and therefore recommended_n) is skipped for this one.
    if days_since_previous is not None:
        entropy = await chore_entropy_repo.get_entropy(session, chore.id)
        prior_state = WelfordState(
            count=entropy.decay_sample_count if entropy else 0,
            mean=float(entropy.decay_days_mean) if entropy else 0.0,
            m2=float(entropy.decay_days_m2) if entropy else 0.0,
        )
        new_state = welford_update(prior_state, days_since_previous)
        recommended = recommended_split(
            n_current=chore.n_current,
            expectation_days=new_state.mean,
            sample_count=new_state.count,
            n_min=chore.n_min,
            n_max=chore.n_max,
        )
        await chore_entropy_repo.upsert_entropy(
            session,
            chore_id=chore.id,
            decay_days_mean=new_state.mean,
            decay_days_m2=new_state.m2,
            decay_sample_count=new_state.count,
            recommended_n=recommended,
            last_computed_at=utc_now(),
        )

    chore.last_completed_at = when
    chore.next_due_at = when + timedelta(days=chore.n_current)

    await session.commit()
    return await chore_service.to_out(session, chore, data_key)
