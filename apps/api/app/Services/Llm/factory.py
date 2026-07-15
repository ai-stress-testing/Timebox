"""Provider construction — the one place that knows every LlmProvider kind.
Dispatch map, not if/elif (constitution Article III.3).
"""
from collections.abc import Callable

from app.Services.Llm.base import LlmProvider
from app.Services.Llm.ollama import OllamaProvider
from app.Services.Llm.openai_compat import OpenAiCompatProvider

_ProviderBuilder = Callable[[str, str, str | None, float], LlmProvider]


def _build_ollama(base_url: str, model: str, api_key: str | None, timeout: float) -> LlmProvider:
    return OllamaProvider(base_url=base_url, model=model, timeout_seconds=timeout)


def _build_openai_compat(
    base_url: str, model: str, api_key: str | None, timeout: float
) -> LlmProvider:
    return OpenAiCompatProvider(
        base_url=base_url, model=model, timeout_seconds=timeout, api_key=api_key
    )


_PROVIDER_BUILDERS: dict[str, _ProviderBuilder] = {
    "ollama": _build_ollama,
    "openai_compat": _build_openai_compat,
}


class UnknownProviderKindError(Exception):
    pass


def build_provider(
    kind: str, base_url: str, model: str, api_key: str | None, timeout: float
) -> LlmProvider:
    builder = _PROVIDER_BUILDERS.get(kind)
    if builder is None:
        raise UnknownProviderKindError(f"unknown llm provider kind: {kind}")
    return builder(base_url, model, api_key, timeout)
