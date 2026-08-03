"""Chore self-correction (spec 008): n-adjustment history + healing-pass log.

`ChoreNHistory` backs `chore_n_history`, a table shared with spec 012 (Chore
Entropy) — both features write rows here, distinguished by `reason`
("healing" here, "entropy"/"manual" elsewhere). Spec 012 had not landed a
model for this table as of this spec shipping (checked: no `chore_n_history`
model existed anywhere in the codebase), so this module defines it; whichever
spec lands second should import this model rather than redefining the table.

`ScheduleHealingLog` is one row per triggering missed-detection pass,
aggregating counts across every chore healed in that pass (not one row per
chore — see Services/chore_healing_service.py).

Both are append-only logs: no soft delete, so neither uses `EntityMixin`
(same shape as `PurgeAudit` in Models/ai.py).
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.Core.ids import uuid7
from app.Models.base import Base, utc_now


class ChoreNHistory(Base):
    __tablename__ = "chore_n_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    chore_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    n_before: Mapped[int] = mapped_column(Integer, nullable=False)
    n_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    schedule_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (Index("idx_chore_n_history_chore", "chore_id", "recorded_at"),)


class ScheduleHealingLog(Base):
    __tablename__ = "schedule_healing_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    schedule_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    occurrences_missed: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrences_healed: Mapped[int] = mapped_column(Integer, nullable=False)
    n_adjustments: Mapped[int] = mapped_column(Integer, nullable=False)
    drift_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    healed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (Index("idx_schedule_healing_log_user", "user_id", "healed_at"),)
