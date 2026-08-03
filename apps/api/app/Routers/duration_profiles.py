"""Duration-profile read route (spec 007) — server-side title hashing, the
frontend estimate-prefill hint's data source. Writes are internal only,
fired from event/chore completion flows, not exposed here.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.duration_profile import DurationProfileOut
from app.Services import duration_profile_service

router = APIRouter(prefix="/duration-profiles", tags=["duration-profiles"])


@router.get("/lookup", response_model=DurationProfileOut)
async def lookup_duration_profile(
    title: str = Query(min_length=1, max_length=300),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> DurationProfileOut:
    profile = await duration_profile_service.lookup_by_title(db, ctx.user_id, title)
    if profile is None:
        raise HTTPException(404, "no duration profile for this title yet")
    return profile
