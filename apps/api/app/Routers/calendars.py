"""Calendar routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.calendar import CalendarCreate, CalendarOut
from app.Services import calendar_service

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("", response_model=list[CalendarOut])
async def list_calendars(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[CalendarOut]:
    return await calendar_service.list_calendars(db, ctx.user_id, ctx.data_key)


@router.post("", response_model=CalendarOut, status_code=201)
async def create_calendar(
    payload: CalendarCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CalendarOut:
    return await calendar_service.create_calendar(db, ctx.user_id, ctx.data_key, payload)
