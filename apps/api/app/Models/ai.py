"""AI sessions — prompt privacy: only the SHA-256 hash of a prompt is stored."""
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, EntityMixin


class AiSession(Base, EntityMixin):
    __tablename__ = "ai_sessions"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    outcome: Mapped[str] = mapped_column(String(16), default="ok", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (Index("idx_ai_sessions_user", "user_id", "created_at"),)


class PurgeAudit(Base):
    __tablename__ = "purge_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[str] = mapped_column(String(36), nullable=False)
    deleted_at: Mapped[str] = mapped_column(String(32), nullable=False)
    purged_at: Mapped[str] = mapped_column(String(32), nullable=False)
