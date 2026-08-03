"""Attention-class service — boot-time seed of the 3 fixed rows (mirrors
`event_type_service.ensure_seeded`'s shape) plus the two lookups that
replace the hardcoded `AttentionClass.active` branches in
`pomodoro_service` and `dispatch_maps/canvas_type.py`.

Global, not user-scoped: production wiring calls `ensure_seeded` once from
`main.py`'s lifespan (see spec 005). `ensure_seeded` is also called
defensively at each lookup site (cheap: a single indexed row-count query,
no-op once seeded) so behavior is correct even before that boot wiring
lands or against a fresh session that predates it.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.attention_class import AttentionClass
from app.Repositories import attention_class_repo

# (value, label, description, pomodoro_applicable, residual_applicable,
#  delay_on_no_complete, default_r, default_alarm_class) — the three rows
# that used to live in dispatch_maps/canvas_type.py::ATTENTION_DEFAULTS.
_SEED: tuple[tuple[str, str, str, bool, bool, bool, float, str | None], ...] = (
    (
        "active",
        "Active",
        "Focused, single-task attention — pomodoro sessions and residual "
        "carry-over apply.",
        True,
        True,
        True,
        0.2,
        None,
    ),
    (
        "involved",
        "Involved",
        "Semi-attended work that doesn't warrant pomodoro gating or "
        "residual carry-over.",
        False,
        False,
        False,
        0.3,
        None,
    ),
    (
        "passive",
        "Passive",
        "Background/low-attention activity — no pomodoro, no residual "
        "carry-over.",
        False,
        False,
        False,
        0.8,
        None,
    ),
)


async def ensure_seeded(session: AsyncSession) -> None:
    """Seed the 3 fixed rows exactly once — a no-op once any row exists."""
    existing = await attention_class_repo.list_all(session)
    if existing:
        return
    for (
        value,
        label,
        description,
        pomodoro_applicable,
        residual_applicable,
        delay_on_no_complete,
        default_r,
        default_alarm_class,
    ) in _SEED:
        attention_class_repo.add_entity(
            session,
            AttentionClass(
                value=value,
                label=label,
                description=description,
                pomodoro_applicable=pomodoro_applicable,
                residual_applicable=residual_applicable,
                delay_on_no_complete=delay_on_no_complete,
                default_r=default_r,
                default_alarm_class=default_alarm_class,
            ),
        )
    await session.commit()


async def list_classes(session: AsyncSession) -> list[AttentionClass]:
    """Same defensive pattern as `event_type_service.list_types`: seed on
    first access (idempotent), then return the live rows."""
    await ensure_seeded(session)
    return await attention_class_repo.list_all(session)


async def is_pomodoro_applicable(session: AsyncSession, value: str) -> bool:
    await ensure_seeded(session)
    row = await attention_class_repo.get_by_value(session, value)
    return row is not None and row.pomodoro_applicable


async def is_residual_applicable(session: AsyncSession, value: str) -> bool:
    await ensure_seeded(session)
    row = await attention_class_repo.get_by_value(session, value)
    return row is not None and row.residual_applicable
