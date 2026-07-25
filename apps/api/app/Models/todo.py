"""Todos — lightweight unscheduled intent; funnels into a calendar Event via
`scheduled_event_id` (plain string cross-reference, no FK constraint, same
convention as Event.calendar_id/residual_of)."""
from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin


class Todo(Base, EntityMixin):
    __tablename__ = "todos"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title_enc: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scheduled_event_id: Mapped[str | None] = mapped_column(String(36), default=None)

    __table_args__ = (
        Index("idx_todos_user", "user_id"),
    )
