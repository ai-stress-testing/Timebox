"""Per-user LLM runtime settings — provider kind, endpoint, model, optional
encrypted API key. Single-row config, not user content: excluded from the
14-day hard-purge sweep (see Services/purge_service.py).
"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, utc_now


class LlmSettings(Base):
    __tablename__ = "llm_settings"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key_enc: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
