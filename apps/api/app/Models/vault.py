"""Vault identity — the only auth table. Stores a one-way verifier, never the secret."""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.Models.base import Base, utc_now


class VaultIdentity(Base):
    __tablename__ = "vault_identity"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    verifier: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
