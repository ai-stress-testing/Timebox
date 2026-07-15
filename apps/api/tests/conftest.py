"""Test fixtures — fresh SQLite per test, ASGI transport, stub LLM provider."""
import os
import uuid

os.environ["TIMEBOX_DATABASE_URL"] = f"sqlite+aiosqlite:///./data/test-{uuid.uuid4().hex}.db"

import pytest
from httpx import ASGITransport, AsyncClient

from app.Core.database import engine, init_models
from app.main import app
from app.Models.base import Base
from app.Services.Llm.base import ChatMessage


class StubProvider:
    """Deterministic LlmProvider stand-in — records prompts for assertions."""

    def __init__(self, reply: str = "") -> None:
        self.reply = reply
        self.calls: list[tuple[ChatMessage, ...]] = []

    @property
    def model(self) -> str:
        return "stub-model"

    async def chat(self, messages: tuple[ChatMessage, ...]) -> str:
        self.calls.append(messages)
        return self.reply

    async def health(self) -> tuple[bool, str | None]:
        return True, None

    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
async def _fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_models()
    app.state.session_store.revoke_all()
    yield


@pytest.fixture
def stub_provider():
    provider = StubProvider()
    original = app.state.llm_provider
    app.state.llm_provider = provider
    yield provider
    app.state.llm_provider = original


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as http:
        yield http


@pytest.fixture
async def unlocked(client: AsyncClient):
    """Generate a key, unlock, return (client, keyfile, headers)."""
    generated = await client.post("/vault/generate")
    assert generated.status_code == 200, generated.text
    keyfile = generated.json()["keyfile"]
    unlocked_res = await client.post("/vault/unlock", json={"keyfile": keyfile})
    assert unlocked_res.status_code == 200, unlocked_res.text
    token = unlocked_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, keyfile, headers
