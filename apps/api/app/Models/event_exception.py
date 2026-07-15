"""Event exceptions — per-occurrence cancellations for a recurring master.

A live row here marks one `occurrence_date` of a master series as removed
(issue #4, `scope="occurrence"`) without touching the master row or
persisting a full event copy. Soft delete via `deleted_at` like every other
table; a live row for a (master_event_id, occurrence_date) pair means "skip
this date" in the expansion read path (`Services/event_service.py`).
"""
from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin

_LIVE_ROW_PREDICATE = text("deleted_at IS NULL")


class EventException(Base, EntityMixin):
    __tablename__ = "event_exceptions"

    master_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    occurrence_date: Mapped[str] = mapped_column(String(10), nullable=False)

    __table_args__ = (
        Index(
            "idx_event_exceptions_live",
            "master_event_id",
            "occurrence_date",
            unique=True,
            sqlite_where=_LIVE_ROW_PREDICATE,
            postgresql_where=_LIVE_ROW_PREDICATE,
        ),
    )
