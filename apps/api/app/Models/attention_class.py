"""Attention-class metadata — the DB-Schemas `attention_classes` table.

Seeded once at boot with exactly 3 fixed rows (active/involved/passive);
read-only via the API. App-level configuration, not user content: no
`user_id`, no encryption, no soft delete — a plain `Base` subclass with
explicit columns rather than `EntityMixin` (see spec 005).
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Core.ids import uuid7
from app.Models.base import Base, utc_now


class AttentionClass(Base):
    __tablename__ = "attention_classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid7)
    value: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pomodoro_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    residual_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    delay_on_no_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    default_r: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    default_alarm_class: Mapped[str | None] = mapped_column(String(24), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
