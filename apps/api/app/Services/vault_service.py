"""Vault service — key-file identity lifecycle. The secret never touches disk."""
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Core.ids import uuid7
from app.Core.sessions import SessionEntry, SessionStore
from app.Models import (
    AiSession,
    Calendar,
    ChoreDefinition,
    ChoreOccurrence,
    Event,
    PomodoroSession,
    ResidualPrompt,
    ScheduleRun,
    TaskResidual,
)
from app.Models.base import utc_now
from app.Repositories import vault_repo
from app.Schemas.vault import Keyfile

_SOFT_DELETE_MODELS = (
    Calendar,
    Event,
    ChoreDefinition,
    ScheduleRun,
    ChoreOccurrence,
    PomodoroSession,
    ResidualPrompt,
    TaskResidual,
    AiSession,
)


class VaultError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def is_registered(session: AsyncSession) -> bool:
    identity = await vault_repo.get_identity(session)
    return identity is not None


async def generate_keyfile(session: AsyncSession) -> Keyfile:
    if await is_registered(session):
        raise VaultError(409, "a key already exists for this vault")
    secret_b64 = crypto.generate_secret()
    user_id = uuid7()
    verifier = crypto.compute_verifier(crypto.decode_secret(secret_b64))
    await vault_repo.create_identity(session, user_id, verifier)
    await session.commit()
    return Keyfile(
        format="timebox-keyfile",
        version=1,
        user_id=user_id,
        secret=secret_b64,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def unlock(
    session: AsyncSession, store: SessionStore, keyfile: Keyfile
) -> SessionEntry:
    identity = await vault_repo.get_identity(session)
    generic = VaultError(401, "unlock failed")
    if identity is None or identity.user_id != keyfile.user_id:
        raise generic
    try:
        secret = crypto.decode_secret(keyfile.secret)
    except Exception as exc:
        raise generic from exc
    if not crypto.verifier_matches(secret, identity.verifier):
        raise generic
    data_key = crypto.derive_data_key(secret)
    return store.create(identity.user_id, data_key)


async def reset_vault(session: AsyncSession, store: SessionStore, user_id: str) -> None:
    now = utc_now()
    for model in _SOFT_DELETE_MODELS:
        stmt = (
            update(model)
            .where(model.user_id == user_id, model.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        await session.execute(stmt)
    await vault_repo.delete_identity(session)
    await session.commit()
    store.revoke_all()
