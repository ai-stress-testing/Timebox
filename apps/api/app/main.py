"""Timebox API — app factory + lifespan. Single user, zero surveillance."""
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.Core.config import settings
from app.Core.database import init_models, session_factory
from app.Core.logging import configure_logging, get_logger
from app.Core.sessions import InMemorySessionStore
from app.Middleware.auth import SessionAuthMiddleware
from app.Middleware.trace import TraceIdMiddleware
from app.Routers import ai, calendars, chores, events, pomodoro, schedule, vault
from app.Services.Llm.ollama import build_default_provider
from app.Services.purge_service import run_purge

_log = get_logger(__name__)

_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_models()
    async with session_factory() as db:
        await run_purge(db)
    _log.info("timebox-api ready")
    yield
    await app.state.llm_provider.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Timebox API", version="0.1.0", lifespan=lifespan)
    app.state.session_store = InMemorySessionStore(ttl_hours=settings.session_ttl_hours)
    app.state.llm_provider = build_default_provider()

    app.add_middleware(SessionAuthMiddleware, store=app.state.session_store)
    app.add_middleware(TraceIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_DEV_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (
        vault.router,
        calendars.router,
        events.router,
        chores.router,
        schedule.router,
        pomodoro.router,
        ai.router,
    ):
        app.include_router(router, prefix=settings.api_prefix)

    @app.get("/health")
    @app.get(f"{settings.api_prefix}/health")
    async def health() -> dict[str, object]:
        return {"ok": True, "service": "timebox-api"}

    return app


app = create_app()
