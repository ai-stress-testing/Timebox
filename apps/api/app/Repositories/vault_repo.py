"""Vault identity queries."""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.vault import VaultIdentity


async def get_identity(session: AsyncSession) -> VaultIdentity | None:
    result = await session.execute(select(VaultIdentity).limit(1))
    return result.scalar_one_or_none()


async def create_identity(session: AsyncSession, user_id: str, verifier: str) -> VaultIdentity:
    identity = VaultIdentity(user_id=user_id, verifier=verifier)
    session.add(identity)
    await session.flush()
    return identity


async def delete_identity(session: AsyncSession) -> None:
    await session.execute(delete(VaultIdentity))
