"""User-defined event types — 7 presets seeded per user, plus custom types."""
from sqlalchemy import Boolean, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin

_UNIQUE_KEY_PREDICATE = text("deleted_at IS NULL")


class EventType(Base, EntityMixin):
    __tablename__ = "event_types"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label_enc: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index(
            "idx_event_types_user_key",
            "user_id",
            "key",
            unique=True,
            sqlite_where=_UNIQUE_KEY_PREDICATE,
            postgresql_where=_UNIQUE_KEY_PREDICATE,
        ),
    )
