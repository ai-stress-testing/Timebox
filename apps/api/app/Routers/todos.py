"""Todo routes — the to-do-to-schedule funnel: thin, validate, delegate, map errors."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.todo import TodoCreate, TodoOut, TodoPatch, TodoScheduleRequest, TodoScheduleResponse
from app.Services import todo_service

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoOut])
async def list_todos(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[TodoOut]:
    return await todo_service.list_todos(db, ctx.user_id, ctx.data_key)


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


@router.post("/{todo_id}/schedule", response_model=TodoScheduleResponse)
async def schedule_todo(
    todo_id: str,
    payload: TodoScheduleRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> TodoScheduleResponse:
    try:
        return await todo_service.schedule_todo(db, ctx.user_id, ctx.data_key, todo_id, payload)
    except todo_service.TodoError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
