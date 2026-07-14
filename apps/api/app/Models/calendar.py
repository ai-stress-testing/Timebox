"""Calendars — color NULL marks the single default calendar (DB-Schemas rule)."""
from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin

_DEFAULT_CALENDAR_PREDICATE = text("color IS NULL AND deleted_at IS NULL")


class Calendar(Base, EntityMixin):
    __tablename__ = "calendars"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name_enc: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), default=None)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index(
            "idx_calendars_default_per_user",
            "user_id",
            unique=True,
            sqlite_where=_DEFAULT_CALENDAR_PREDICATE,
            postgresql_where=_DEFAULT_CALENDAR_PREDICATE,
        ),
    )
