"""Chore routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.chore import ChoreComplete, ChoreCreate, ChoreOut, ChorePatch
from app.Services import chore_entropy_service, chore_service

router = APIRouter(prefix="/chores", tags=["chores"])


@router.get("", response_model=list[ChoreOut])
async def list_chores(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> list[ChoreOut]:
    return await chore_service.list_chores(db, ctx.user_id, ctx.data_key)


@router.post("", response_model=ChoreOut, status_code=201)
async def create_chore(
    payload: ChoreCreate,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> ChoreOut:
    return await chore_service.create_chore(db, ctx.user_id, ctx.data_key, payload)


@router.patch("/{chore_id}", response_model=ChoreOut)
async def patch_chore(
    chore_id: str,
    payload: ChorePatch,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> ChoreOut:
    try:
        return await chore_service.patch_chore(db, ctx.user_id, ctx.data_key, chore_id, payload)
    except chore_service.ChoreError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{chore_id}/complete", response_model=ChoreOut)
async def complete_chore(
    chore_id: str,
    payload: ChoreComplete,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> ChoreOut:
    try:
        return await chore_entropy_service.record_completion(
            db, ctx.user_id, ctx.data_key, chore_id, payload.completed_at
        )
    except chore_service.ChoreError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.delete("/{chore_id}", status_code=204)
async def delete_chore(
    chore_id: str,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await chore_service.delete_chore(db, ctx.user_id, chore_id)
    except chore_service.ChoreError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
