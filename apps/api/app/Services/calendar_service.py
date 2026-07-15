"""Calendar service — default calendar bootstrap + CRUD mapping."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Models.calendar import Calendar
from app.Repositories import calendar_repo
from app.Schemas.base import CalendarColor
from app.Schemas.calendar import CalendarCreate, CalendarOut

_DEFAULT_CALENDAR_NAME = "Timebox"


def _to_out(calendar: Calendar, data_key: bytes) -> CalendarOut:
    color = CalendarColor(calendar.color) if calendar.color else None
    return CalendarOut(
        id=calendar.id,
        name=crypto.decrypt_field(data_key, calendar.name_enc),
        color=color,
        is_visible=calendar.is_visible,
        created_at=calendar.created_at,
        updated_at=calendar.updated_at,
    )


async def ensure_default_calendar(
    session: AsyncSession, user_id: str, data_key: bytes
) -> Calendar:
    existing = await calendar_repo.get_default_calendar(session, user_id)
    if existing is not None:
        return existing
    calendar = Calendar(
        user_id=user_id,
        name_enc=crypto.encrypt_field(data_key, _DEFAULT_CALENDAR_NAME),
        color=None,
    )
    calendar_repo.add_calendar(session, calendar)
    await session.commit()
    return calendar


async def list_calendars(
    session: AsyncSession, user_id: str, data_key: bytes
) -> list[CalendarOut]:
    await ensure_default_calendar(session, user_id, data_key)
    calendars = await calendar_repo.list_calendars(session, user_id)
    return [_to_out(calendar, data_key) for calendar in calendars]


async def create_calendar(
    session: AsyncSession, user_id: str, data_key: bytes, payload: CalendarCreate
) -> CalendarOut:
    color = payload.color.value if payload.color else "slate"
    calendar = Calendar(
        user_id=user_id,
        name_enc=crypto.encrypt_field(data_key, payload.name),
        color=color,
    )
    calendar_repo.add_calendar(session, calendar)
    await session.commit()
    return _to_out(calendar, data_key)
