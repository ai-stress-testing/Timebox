"""Pomodoro + residual prompt routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.pomodoro import (
    FinishResponse,
    PromptOut,
    PromptRespond,
    PromptRespondResponse,
    SessionFinish,
    SessionOut,
    SessionStart,
)
from app.Services import pomodoro_service

router = APIRouter(prefix="/pomodoro", tags=["pomodoro"])


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def start_session(
    payload: SessionStart,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> SessionOut:
    try:
        return await pomodoro_service.start_session(db, ctx.user_id, ctx.data_key, payload)
    except pomodoro_service.PomodoroError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/sessions/{session_id}/finish", response_model=FinishResponse)
async def finish_session(
    session_id: str,
    payload: SessionFinish,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> FinishResponse:
    try:
        return await pomodoro_service.finish_session(
            db, ctx.user_id, ctx.data_key, session_id, payload
        )
    except pomodoro_service.PomodoroError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[SessionOut]:
    return await pomodoro_service.list_sessions(db, ctx.user_id, ctx.data_key, limit)


@router.get("/prompts", response_model=list[PromptOut])
async def list_prompts(
    status: str | None = Query(default=None),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[PromptOut]:
    return await pomodoro_service.list_prompts(db, ctx.user_id, status)


@router.post("/prompts/{prompt_id}/respond", response_model=PromptRespondResponse)
async def respond_to_prompt(
    prompt_id: str,
    payload: PromptRespond,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> PromptRespondResponse:
    try:
        return await pomodoro_service.respond_to_prompt(db, ctx.user_id, prompt_id, payload)
    except pomodoro_service.PomodoroError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
