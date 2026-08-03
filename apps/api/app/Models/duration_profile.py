"""Duration profiles (spec 007): running Welford mean/variance of how long a
label (event title hash) or chore actually takes, keyed one row per
(user, label_hash) or (user, chore_id). Feeds estimate prefill and
`ChoreDefinition.mc_weight`.
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin

_LABEL_UNIQUE_PREDICATE = text("label_hash IS NOT NULL AND deleted_at IS NULL")
_CHORE_UNIQUE_PREDICATE = text("chore_id IS NOT NULL AND deleted_at IS NULL")


class DurationProfile(Base, EntityMixin):
    __tablename__ = "duration_profiles"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    label_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    chore_id: Mapped[str | None] = mapped_column(String(36), default=None)
    attention_class: Mapped[str | None] = mapped_column(String(16), default=None)

    total_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_mean: Mapped[float] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    total_m2: Mapped[float] = mapped_column(Numeric(12, 4), default=0, nullable=False)

    meaningful_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meaningful_mean: Mapped[float] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    meaningful_m2: Mapped[float] = mapped_column(Numeric(12, 4), default=0, nullable=False)

    mc_weight: Mapped[float] = mapped_column(Numeric(6, 4), default=1.0, nullable=False)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (
        Index(
            "idx_duration_profiles_label_unique",
            "user_id",
            "label_hash",
            unique=True,
            sqlite_where=_LABEL_UNIQUE_PREDICATE,
            postgresql_where=_LABEL_UNIQUE_PREDICATE,
        ),
        Index(
            "idx_duration_profiles_chore_unique",
            "user_id",
            "chore_id",
            unique=True,
            sqlite_where=_CHORE_UNIQUE_PREDICATE,
            postgresql_where=_CHORE_UNIQUE_PREDICATE,
        ),
    )
