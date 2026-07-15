"""AI routes — Ollama-only provider behind the LlmProvider seam."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.Core.config import settings
from app.Core.database import get_session
from app.Middleware.prompt_sanitiser import PromptRejected
from app.Routers.deps import SessionContext, get_session_context
from app.Schemas.ai import AiHealthResponse, TimeboxRequest, TimeboxResponse
from app.Services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health", response_model=AiHealthResponse)
async def ai_health(request: Request) -> AiHealthResponse:
    provider = request.app.state.llm_provider
    ok, detail = await provider.health()
    return AiHealthResponse(
        ok=ok, model=provider.model, base_url=settings.ollama_base_url, detail=detail
    )


@router.post("/timebox", response_model=TimeboxResponse)
async def timebox(
    payload: TimeboxRequest,
    request: Request,
    ctx: SessionContext = Depends(get_session_context),
    db: AsyncSession = Depends(get_session),
) -> TimeboxResponse:
    provider = request.app.state.llm_provider
    try:
        return await ai_service.propose_timebox(db, ctx.user_id, provider, payload)
    except PromptRejected as exc:
        raise HTTPException(400, "request could not be processed") from exc
    except ai_service.AiError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
