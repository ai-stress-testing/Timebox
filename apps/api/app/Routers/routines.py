"""Routine routes — thin: validate, delegate, map service errors to HTTP.

Two routers live in this module because the spec's run-advance/finish/abandon
paths are addressed by run id alone (`/runs/{runId}/...`), not nested under
`/routines/{id}` — see the "wire me in" note in the final report for exactly
how `main.py` should mount both.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.routine import (
    RoutineAdvanceRequest,
    RoutineCreate,
    RoutineOut,
    RoutinePatch,
    RoutineRunOut,
    RoutineScheduleRequest,
    RoutineScheduleResponse,
    RoutineStepCreate,
    RoutineStepOut,
    RoutineStepPatch,
    RoutineStepReorderRequest,
)
from app.Services import routine_service

router = APIRouter(prefix="/routines", tags=["routines"])
runs_router = APIRouter(prefix="/runs", tags=["routines"])


@router.get("", response_model=list[RoutineOut])
async def list_routines(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[RoutineOut]:
    return await routine_service.list_routines(db, ctx.user_id, ctx.data_key)


@router.post("", response_model=RoutineOut, status_code=201)
async def create_routine(
    payload: RoutineCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineOut:
    return await routine_service.create_routine(db, ctx.user_id, ctx.data_key, payload)


@router.patch("/{routine_id}", response_model=RoutineOut)
async def patch_routine(
    routine_id: str,
    payload: RoutinePatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineOut:
    try:
        return await routine_service.patch_routine(
            db, ctx.user_id, ctx.data_key, routine_id, payload
        )
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.delete("/{routine_id}", status_code=204)
async def delete_routine(
    routine_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await routine_service.delete_routine(db, ctx.user_id, routine_id)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/{routine_id}/steps", response_model=list[RoutineStepOut])
async def list_steps(
    routine_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[RoutineStepOut]:
    try:
        return await routine_service.list_steps(db, ctx.user_id, ctx.data_key, routine_id)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{routine_id}/steps", response_model=RoutineStepOut, status_code=201)
async def add_step(
    routine_id: str,
    payload: RoutineStepCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineStepOut:
    try:
        return await routine_service.add_step(db, ctx.user_id, ctx.data_key, routine_id, payload)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch("/{routine_id}/steps/{step_id}", response_model=RoutineStepOut)
async def patch_step(
    routine_id: str,
    step_id: str,
    payload: RoutineStepPatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineStepOut:
    try:
        return await routine_service.patch_step(
            db, ctx.user_id, ctx.data_key, routine_id, step_id, payload
        )
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.delete("/{routine_id}/steps/{step_id}", status_code=204)
async def delete_step(
    routine_id: str,
    step_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await routine_service.delete_step(db, ctx.user_id, ctx.data_key, routine_id, step_id)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{routine_id}/steps/reorder", response_model=list[RoutineStepOut])
async def reorder_steps(
    routine_id: str,
    payload: RoutineStepReorderRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[RoutineStepOut]:
    try:
        return await routine_service.reorder_steps(
            db, ctx.user_id, ctx.data_key, routine_id, payload.ordered_step_ids
        )
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{routine_id}/runs", response_model=RoutineRunOut, status_code=201)
async def start_run(
    routine_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineRunOut:
    try:
        return await routine_service.start_run(db, ctx.user_id, ctx.data_key, routine_id)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/{routine_id}/runs", response_model=list[RoutineRunOut])
async def list_runs(
    routine_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[RoutineRunOut]:
    try:
        return await routine_service.list_runs(db, ctx.user_id, ctx.data_key, routine_id, limit)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{routine_id}/schedule", response_model=RoutineScheduleResponse)
async def schedule_routine(
    routine_id: str,
    payload: RoutineScheduleRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineScheduleResponse:
    try:
        return await routine_service.schedule_routine(
            db, ctx.user_id, ctx.data_key, routine_id, payload
        )
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@runs_router.post("/{run_id}/steps/{step_run_id}/advance", response_model=RoutineRunOut)
async def advance_step(
    run_id: str,
    step_run_id: str,
    payload: RoutineAdvanceRequest,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineRunOut:
    try:
        return await routine_service.advance_step(
            db, ctx.user_id, ctx.data_key, run_id, step_run_id, payload
        )
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@runs_router.post("/{run_id}/finish", response_model=RoutineRunOut)
async def finish_run(
    run_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineRunOut:
    try:
        return await routine_service.finish_run(db, ctx.user_id, ctx.data_key, run_id)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@runs_router.post("/{run_id}/abandon", response_model=RoutineRunOut)
async def abandon_run(
    run_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> RoutineRunOut:
    try:
        return await routine_service.abandon_run(db, ctx.user_id, ctx.data_key, run_id)
    except routine_service.RoutineError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
