"""Event-type routes — presets + custom, thin: validate, delegate, map errors."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.event import EventTypeCreate, EventTypePatch, EventTypeSummary
from app.Services import event_type_service

router = APIRouter(prefix="/event-types", tags=["event-types"])


@router.get("", response_model=list[EventTypeSummary])
async def list_event_types(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[EventTypeSummary]:
    return await event_type_service.list_types(db, ctx.user_id, ctx.data_key)


@router.post("", response_model=EventTypeSummary, status_code=201)
async def create_event_type(
    payload: EventTypeCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> EventTypeSummary:
    try:
        return await event_type_service.create_type(db, ctx.user_id, ctx.data_key, payload)
    except event_type_service.EventTypeError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch("/{event_type_id}", response_model=EventTypeSummary)
async def patch_event_type(
    event_type_id: str,
    payload: EventTypePatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> EventTypeSummary:
    try:
        return await event_type_service.patch_type(
            db, ctx.user_id, ctx.data_key, event_type_id, payload
        )
    except event_type_service.EventTypeError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.delete("/{event_type_id}", status_code=204)
async def delete_event_type(
    event_type_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await event_type_service.delete_type(db, ctx.user_id, event_type_id)
    except event_type_service.EventTypeError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
