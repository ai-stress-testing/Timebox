"""Singleton async engine + session factory (NASA rule 3: infra created once at boot).

Prototype: SQLite via aiosqlite. Production swap: set TIMEBOX_DATABASE_URL to
PostgreSQL 16 — nothing above this module changes. Alembic deferred (see
constitution Article IV); create_all runs at startup.
"""
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.Core.config import settings
from app.Models.base import Base

_SQLITE_PREFIX = "sqlite"


def _ensure_sqlite_dir(database_url: str) -> None:
    is_sqlite_file = database_url.startswith(_SQLITE_PREFIX) and ":memory:" not in database_url
    if not is_sqlite_file:
        return
    db_path = Path(database_url.rsplit("///", 1)[-1])
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_async_engine(settings.database_url, echo=False)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
