"""Timebox API — app factory + lifespan. Single user, zero surveillance."""
import asyncio
import os
from contextlib import asynccontextmanager, suppress
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.Core.config import settings
from app.Core.database import init_models, session_factory
from app.Core.logging import configure_logging, get_logger
from app.Core.sessions import InMemorySessionStore
from app.Middleware.auth import SessionAuthMiddleware
from app.Middleware.trace import TraceIdMiddleware
from app.Routers import (
    ai,
    attention_classes,
    calendars,
    canvas,
    chores,
    duration_profiles,
    event_types,
    events,
    pomodoro,
    routines,
    schedule,
    todos,
    vault,
)
from app.Services import attention_class_service
from app.Services.chore_missed_detection_service import run_missed_detection
from app.Services.Llm.ollama import build_default_provider
from app.Services.purge_service import run_purge

_log = get_logger(__name__)

_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


_PURGE_INTERVAL_SECONDS = 24 * 60 * 60
_MISSED_DETECTION_INTERVAL_SECONDS = 60 * 60


async def _purge_daily() -> None:
    """The pg_cron stand-in: enforce the 14-day hard-purge contract daily."""
    while True:
        async with session_factory() as db:
            await run_purge(db)
        await asyncio.sleep(_PURGE_INTERVAL_SECONDS)


async def _missed_detection_hourly() -> None:
    """Spec 008 part 1+2: transition passed-window occurrences, then heal
    chronically-missed chores' cadence, once an hour."""
    while True:
        async with session_factory() as db:
            await run_missed_detection(db)
        await asyncio.sleep(_MISSED_DETECTION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_models()
    async with session_factory() as db:
        await attention_class_service.ensure_seeded(db)
    purge_task = asyncio.create_task(_purge_daily())
    missed_detection_task = asyncio.create_task(_missed_detection_hourly())
    _log.info("timebox-api ready")
    yield
    purge_task.cancel()
    missed_detection_task.cancel()
    with suppress(asyncio.CancelledError):
        await purge_task
    with suppress(asyncio.CancelledError):
        await missed_detection_task
    await app.state.llm_provider.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Timebox API", version="0.1.0", lifespan=lifespan)
    app.state.session_store = InMemorySessionStore(
        ttl_hours=settings.session_ttl_hours,
        max_lifetime_hours=settings.session_max_lifetime_hours,
    )
    app.state.llm_provider = build_default_provider()

    app.add_middleware(
        SessionAuthMiddleware,
        store=app.state.session_store,
        api_prefix=settings.api_prefix,
    )
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
        event_types.router,
        chores.router,
        schedule.router,
        pomodoro.router,
        todos.router,
        routines.router,
        routines.runs_router,
        canvas.router,
        ai.router,
        attention_classes.router,
        duration_profiles.router,
    ):
        app.include_router(router, prefix=settings.api_prefix)

    @app.get("/health")
    @app.get(f"{settings.api_prefix}/health")
    async def health() -> dict[str, object]:
        return {"ok": True, "service": "timebox-api"}

    web_dir = settings.web_dist_dir
    if web_dir and os.path.isdir(web_dir):
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app


app = create_app()
