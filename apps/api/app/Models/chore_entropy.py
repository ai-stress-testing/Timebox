"""Chore decay-rate tracking (spec 012): completion log + Welford stats.

`ChoreCompletion` is an append-only log of every "chore marked done" event.
`ChoreEntropy` is a sibling, one-row-per-chore table holding the running
Welford mean/variance of `days_since_previous` plus the cached
`recommended_n` — kept out of `ChoreDefinition` itself so the hot-path chore
list query never has to touch Welford state.
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin

_UNIQUE_CHORE_PREDICATE = text("deleted_at IS NULL")


class ChoreCompletion(Base, EntityMixin):
    __tablename__ = "chore_completions"

    chore_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Null for a chore's first-ever completion (no prior last_completed_at to
    # diff against) — the Welford update is skipped for that row too.
    days_since_previous: Mapped[float | None] = mapped_column(Numeric(6, 2), default=None)

    __table_args__ = (
        Index("idx_chore_completions_chore", "chore_id", "completed_at"),
    )


class ChoreEntropy(Base, EntityMixin):
    __tablename__ = "chore_entropy"

    chore_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decay_days_mean: Mapped[float] = mapped_column(Numeric(6, 3), default=0, nullable=False)
    decay_days_m2: Mapped[float] = mapped_column(Numeric(10, 4), default=0, nullable=False)
    decay_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommended_n: Mapped[int | None] = mapped_column(Integer, default=None)
    last_computed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (
        Index(
            "idx_chore_entropy_chore_unique",
            "chore_id",
            unique=True,
            sqlite_where=_UNIQUE_CHORE_PREDICATE,
            postgresql_where=_UNIQUE_CHORE_PREDICATE,
        ),
    )
