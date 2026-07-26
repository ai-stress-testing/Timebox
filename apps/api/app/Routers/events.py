"""Event routes — thin: validate, delegate, map service errors to HTTP."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.base import UtcDateTime
from app.Schemas.event import (
    EventCreate,
    EventOut,
    EventPatch,
    EventSplitRequest,
    EventSplitResponse,
    EventTitleSuggestion,
)
from app.Services import event_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
async def list_events(
    start: UtcDateTime = Query(...),
    end: UtcDateTime = Query(...),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[EventOut]:
    return await event_service.list_events(db, ctx.user_id, ctx.data_key, start, end)


# Declared before /{event_id} so "titles" is not captured as an event id.
@router.get("/titles", response_model=list[EventTitleSuggestion])
async def list_title_suggestions(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[EventTitleSuggestion]:
    return await event_service.title_suggestions(db, ctx.user_id, ctx.data_key)


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    payload: EventCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> EventOut:
    try:
        return await event_service.create_event(db, ctx.user_id, ctx.data_key, payload)
    except event_service.EventError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> EventOut:
    try:
        return await event_service.get_event(db, ctx.user_id, ctx.data_key, event_id)
    except event_service.EventError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch("/{event_id}", response_model=EventOut)
async def patch_event(
    event_id: str,
    payload: EventPatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> EventOut:
    try:
        return await event_service.patch_event(db, ctx.user_id, ctx.data_key, event_id, payload)
    except event_service.EventError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{event_id}/split", response_model=EventSplitResponse)
async def split_event(
    event_id: str,
    payload: EventSplitRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> EventSplitResponse:
    try:
        first, second = await event_service.split_event(
            db, ctx.user_id, ctx.data_key, event_id, payload.split_at
        )
    except event_service.EventError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return EventSplitResponse(first=first, second=second)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: str,
    scope: Literal["all", "occurrence", "following"] = Query(default="all"),
    occurrence_date: str | None = Query(default=None),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await event_service.delete_event(db, ctx.user_id, event_id, scope, occurrence_date)
    except event_service.EventError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
