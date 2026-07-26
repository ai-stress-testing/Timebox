"""Per-user LLM settings persistence — single row per user, config not secret
content beyond the API key field (which callers must encrypt before it lands here).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.base import utc_now
from app.Models.llm_settings import LlmSettings


async def get_settings(session: AsyncSession, user_id: str) -> LlmSettings | None:
    stmt = select(LlmSettings).where(LlmSettings.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_settings(
    session: AsyncSession,
    user_id: str,
    provider_kind: str,
    base_url: str,
    model: str,
    api_key_enc: str | None,
) -> LlmSettings:
    existing = await get_settings(session, user_id)
    if existing is None:
        existing = LlmSettings(user_id=user_id)
        session.add(existing)
    existing.provider_kind = provider_kind
    existing.base_url = base_url
    existing.model = model
    existing.api_key_enc = api_key_enc
    existing.updated_at = utc_now()
    return existing
