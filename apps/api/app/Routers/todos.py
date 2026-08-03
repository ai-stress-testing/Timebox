"""Todo routes — the to-do-to-schedule funnel: thin, validate, delegate, map errors."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.todo import (
    BatchScheduleRequest,
    BatchScheduleResponse,
    TodoCreate,
    TodoOut,
    TodoPatch,
)
from app.Services import todo_service

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoOut])
async def list_todos(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[TodoOut]:
    return await todo_service.list_todos(db, ctx.user_id, ctx.data_key)


# Declared before /{todo_id}-shaped routes so "batch-schedule" is never
# captured as a todo id (same convention as events' "/titles", see
# Routers/events.py) — POST here vs. PATCH /{todo_id} can't actually collide
# on method, but keeping static-before-dynamic ordering regardless.
@router.post("/batch-schedule", response_model=BatchScheduleResponse)
async def batch_schedule_todos(
    payload: BatchScheduleRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> BatchScheduleResponse:
    return await todo_service.batch_schedule(db, ctx.user_id, ctx.data_key, payload)


@router.post("", response_model=TodoOut, status_code=201)
async def create_todo(
    payload: TodoCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> TodoOut:
    return await todo_service.create_todo(db, ctx.user_id, ctx.data_key, payload)


@router.patch("/{todo_id}", response_model=TodoOut)
async def patch_todo(
    todo_id: str,
    payload: TodoPatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> TodoOut:
    try:
        return await todo_service.patch_todo(db, ctx.user_id, ctx.data_key, todo_id, payload)
    except todo_service.TodoError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await todo_service.delete_todo(db, ctx.user_id, todo_id)
    except todo_service.TodoError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
