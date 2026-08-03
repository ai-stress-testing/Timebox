"""Ollama provider's Docker-internal fallback (primary unreachable -> retry
against a distinct fallback base URL, e.g. the docker-compose `ollama`
sidecar). No live network calls — httpx.MockTransport routes by host.
"""
import httpx
import pytest

from app.Services.Llm.base import ChatMessage, LlmUnavailableError
from app.Services.Llm.ollama import OllamaProvider

_PRIMARY = "http://host.docker.internal:11434"
_FALLBACK = "http://ollama:11434"
_MESSAGES = (ChatMessage(role="user", content="hi"),)


class _Reachability:
    """Mutable per-host up/down flags a single MockTransport reads live, so a
    test can flip them between calls without touching httpx internals."""

    def __init__(self, *, primary_up: bool, fallback_up: bool) -> None:
        self.primary_up = primary_up
        self.fallback_up = fallback_up


def _transport(reachability: _Reachability) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        up = reachability.primary_up if host == "host.docker.internal" else reachability.fallback_up
        if not up:
            raise httpx.ConnectError("connection refused", request=request)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        return httpx.Response(200, json={"message": {"content": f"served-by:{host}"}})

    return httpx.MockTransport(handler)


def _provider(reachability: _Reachability, fallback_base_url: str | None = _FALLBACK) -> OllamaProvider:
    return OllamaProvider(
        base_url=_PRIMARY,
        model="llama3.2",
        timeout_seconds=5.0,
        fallback_base_url=fallback_base_url,
        transport=_transport(reachability),
    )


async def test_primary_reachable_never_touches_fallback() -> None:
    provider = _provider(_Reachability(primary_up=True, fallback_up=True))
    reply = await provider.chat(_MESSAGES)
    assert reply == "served-by:host.docker.internal"
    assert provider.base_url == _PRIMARY
    await provider.close()


async def test_primary_unreachable_falls_back_automatically() -> None:
    provider = _provider(_Reachability(primary_up=False, fallback_up=True))
    reply = await provider.chat(_MESSAGES)
    assert reply == "served-by:ollama"
    assert provider.base_url == _FALLBACK
    await provider.close()


async def test_health_falls_back_when_primary_unreachable() -> None:
    provider = _provider(_Reachability(primary_up=False, fallback_up=True))
    ok, detail = await provider.health()
    assert ok is True
    assert detail is None
    assert provider.base_url == _FALLBACK
    await provider.close()


async def test_both_unreachable_raises_llm_unavailable() -> None:
    provider = _provider(_Reachability(primary_up=False, fallback_up=False))
    with pytest.raises(LlmUnavailableError):
        await provider.chat(_MESSAGES)
    await provider.close()


async def test_no_fallback_configured_raises_on_primary_failure() -> None:
    provider = _provider(_Reachability(primary_up=False, fallback_up=True), fallback_base_url=None)
    with pytest.raises(LlmUnavailableError):
        await provider.chat(_MESSAGES)
    await provider.close()


async def test_fallback_equal_to_primary_is_a_no_op() -> None:
    """A misconfigured fallback identical to the primary must not be treated
    as a distinct retry target — same shape as "no fallback configured"."""
    provider = _provider(_Reachability(primary_up=False, fallback_up=True), fallback_base_url=_PRIMARY)
    with pytest.raises(LlmUnavailableError):
        await provider.chat(_MESSAGES)
    await provider.close()


async def test_primary_recovers_after_a_fallback_call() -> None:
    """The retry is stateless per-call — once the primary is reachable again
    it's used again, not "sticky" to whichever URL last served a request."""
    reachability = _Reachability(primary_up=False, fallback_up=True)
    provider = _provider(reachability)

    await provider.chat(_MESSAGES)
    assert provider.base_url == _FALLBACK

    reachability.primary_up = True
    await provider.chat(_MESSAGES)
    assert provider.base_url == _PRIMARY
    await provider.close()
