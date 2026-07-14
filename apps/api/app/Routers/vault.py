"""Vault routes — generate / unlock / status / lock / reset."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.vault import (
    GenerateResponse,
    ResetRequest,
    UnlockRequest,
    UnlockResponse,
    VaultStatusResponse,
)
from app.Services import vault_service

router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/status", response_model=VaultStatusResponse)
async def vault_status(db: AsyncSession = Depends(get_session)) -> VaultStatusResponse:
    return VaultStatusResponse(registered=await vault_service.is_registered(db))


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: Request, db: AsyncSession = Depends(get_session)) -> GenerateResponse:
    try:
        keyfile = await vault_service.generate_keyfile(db)
    except vault_service.VaultError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return GenerateResponse(keyfile=keyfile)


@router.post("/unlock", response_model=UnlockResponse)
async def unlock(
    payload: UnlockRequest, request: Request, db: AsyncSession = Depends(get_session)
) -> UnlockResponse:
    store = request.app.state.session_store
    try:
        entry = await vault_service.unlock(db, store, payload.keyfile)
    except vault_service.VaultError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return UnlockResponse(token=entry.token, user_id=entry.user_id, expires_at=entry.expires_at)


@router.post("/lock", status_code=204)
async def lock(request: Request, ctx: SessionContext = Depends(get_session_context)) -> None:
    request.app.state.session_store.revoke(ctx.token)


@router.post("/reset", status_code=204)
async def reset(
    payload: ResetRequest,
    request: Request,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    store = request.app.state.session_store
    await vault_service.reset_vault(db, store, ctx.user_id)
