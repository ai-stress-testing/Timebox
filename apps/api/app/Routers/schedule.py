"""Schedule routes — Monte Carlo runs and apply-to-calendar."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.schedule import ApplyResponse, RunDetailOut, RunOut, RunRequest
from app.Services import schedule_service

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/runs", response_model=RunDetailOut, status_code=201)
async def create_run(
    payload: RunRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RunDetailOut:
    return await schedule_service.create_run(db, ctx.user_id, ctx.data_key, payload)


@router.get("/runs", response_model=list[RunOut])
async def list_runs(
    limit: int = Query(default=10, ge=1, le=50),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[RunOut]:
    return await schedule_service.list_runs(db, ctx.user_id, limit)


@router.get("/runs/{run_id}", response_model=RunDetailOut)
async def get_run(
    run_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RunDetailOut:
    try:
        return await schedule_service.get_run_detail(db, ctx.user_id, ctx.data_key, run_id)
    except schedule_service.ScheduleError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/runs/{run_id}/apply", response_model=ApplyResponse)
async def apply_run(
    run_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> ApplyResponse:
    try:
        return await schedule_service.apply_run(db, ctx.user_id, ctx.data_key, run_id)
    except schedule_service.ScheduleError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
