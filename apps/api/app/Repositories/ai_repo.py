"""AI session persistence — hash only, never prompt content."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.Models.ai import AiSession


def add_ai_session(session: AsyncSession, ai_session: AiSession) -> AiSession:
    session.add(ai_session)
    return ai_session
