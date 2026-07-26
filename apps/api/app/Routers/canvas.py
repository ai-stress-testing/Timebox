"""Canvas routes — thin: validate, delegate, map service errors to HTTP."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.canvas import (
    CanvasAlarmCreate,
    CanvasAlarmOut,
    CanvasAlarmPatch,
    CanvasItemCreate,
    CanvasItemOut,
    CanvasItemPatch,
)
from app.Services import canvas_service

router = APIRouter(prefix="/canvas", tags=["canvas"])


@router.get("/items", response_model=list[CanvasItemOut])
async def list_items(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[CanvasItemOut]:
    return await canvas_service.list_items(db, ctx.user_id, ctx.data_key)


@router.post("/items", response_model=CanvasItemOut, status_code=201)
async def create_item(
    payload: CanvasItemCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasItemOut:
    try:
        return await canvas_service.create_timer(db, ctx.user_id, ctx.data_key, payload)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch("/items/{item_id}", response_model=CanvasItemOut)
async def patch_item(
    item_id: str,
    payload: CanvasItemPatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasItemOut:
    try:
        return await canvas_service.edit_item(db, ctx.user_id, ctx.data_key, item_id, payload)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/items/{item_id}/start", response_model=CanvasItemOut)
async def start_item(
    item_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasItemOut:
    try:
        return await canvas_service.start_item(db, ctx.user_id, ctx.data_key, item_id)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/items/{item_id}/pause", response_model=CanvasItemOut)
async def pause_item(
    item_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasItemOut:
    try:
        return await canvas_service.pause_item(db, ctx.user_id, ctx.data_key, item_id)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/items/{item_id}/reset", response_model=CanvasItemOut)
async def reset_item(
    item_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasItemOut:
    try:
        return await canvas_service.reset_item(db, ctx.user_id, ctx.data_key, item_id)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await canvas_service.delete_item(db, ctx.user_id, item_id)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/items/{item_id}/alarms", response_model=CanvasAlarmOut, status_code=201)
async def create_alarm(
    item_id: str,
    payload: CanvasAlarmCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasAlarmOut:
    try:
        return await canvas_service.create_alarm(db, ctx.user_id, item_id, payload)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch("/alarms/{alarm_id}", response_model=CanvasAlarmOut)
async def patch_alarm(
    alarm_id: str,
    payload: CanvasAlarmPatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> CanvasAlarmOut:
    try:
        return await canvas_service.patch_alarm(db, ctx.user_id, alarm_id, payload)
    except canvas_service.CanvasError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
