"""Chore definitions — every-n-days living frequency with bounds (DB-Schemas.md)."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin


class ChoreDefinition(Base, EntityMixin):
    __tablename__ = "chore_definitions"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name_enc: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    attention_class: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), default=None)

    n_original: Mapped[int] = mapped_column(Integer, nullable=False)
    n_current: Mapped[int] = mapped_column(Integer, nullable=False)
    n_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    n_max: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    preferred_days: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    avoid_days: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    preferred_time_start: Mapped[str | None] = mapped_column(String(5), default=None)
    preferred_time_end: Mapped[str | None] = mapped_column(String(5), default=None)

    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mc_weight: Mapped[float] = mapped_column(Numeric(6, 4), default=1.0, nullable=False)

    __table_args__ = (
        CheckConstraint("estimated_minutes > 0", name="chk_estimated_positive"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="chk_priority_range"),
        CheckConstraint("n_current >= 1 AND n_original >= 1", name="chk_n_positive"),
        Index("idx_chore_def_user", "user_id"),
    )
