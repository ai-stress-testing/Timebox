"""AI routes — local LLM provider (per-user chosen, or the env default) behind
the LlmProvider seam. The api_key never leaves the server: only has_api_key does.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.database import get_session
from app.Middleware.prompt_sanitiser import PromptRejected
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.ai import (
    AiHealthResponse,
    LlmSettingsIn,
    LlmSettingsOut,
    TimeboxRequest,
    TimeboxResponse,
)
from app.Services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/settings", response_model=LlmSettingsOut)
async def get_llm_settings(
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> LlmSettingsOut:
    return await ai_service.get_llm_settings(db, ctx.user_id)


@router.put("/settings", response_model=LlmSettingsOut)
async def put_llm_settings(
    payload: LlmSettingsIn,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> LlmSettingsOut:
    return await ai_service.save_llm_settings(db, ctx.user_id, ctx.data_key, payload)


@router.get("/health", response_model=AiHealthResponse)
async def ai_health(
    request: Request,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> AiHealthResponse:
    provider, owns_client = await ai_service.resolve_provider(
        db, ctx.user_id, ctx.data_key, request.app.state.llm_provider
    )
    try:
        ok, detail = await provider.health()
        return AiHealthResponse(
            ok=ok, model=provider.model, base_url=provider.base_url, detail=detail
        )
    finally:
        if owns_client:
            await provider.close()


@router.post("/timebox", response_model=TimeboxResponse)
async def timebox(
    payload: TimeboxRequest,
    request: Request,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> TimeboxResponse:
    provider, owns_client = await ai_service.resolve_provider(
        db, ctx.user_id, ctx.data_key, request.app.state.llm_provider
    )
    try:
        return await ai_service.propose_timebox(db, ctx.user_id, provider, payload)
    except PromptRejected as exc:
        raise HTTPException(400, "request could not be processed") from exc
    except ai_service.AiError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    finally:
        if owns_client:
            await provider.close()
