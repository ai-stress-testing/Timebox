"""Prompt sanitiser — every user string bound for the LLM passes through here.
Applied inside the AI service path so no route can bypass it.
Rejections are logged as security events with the prompt HASH only.
"""
from app.Core import crypto
from app.Core.config import settings
from app.Core.logging import get_logger
from app.Core.patterns import CONTROL_CHARS, INJECTION_PATTERNS

_log = get_logger(__name__)


class PromptRejected(Exception):
    """Generic rejection — callers must not leak which rule triggered."""


def _log_security_event(reason: str, text: str) -> None:
    _log.warning(f"prompt rejected reason={reason} prompt_sha256={crypto.sha256_hex(text)}")


def sanitise_prompt(text: str) -> str:
    stripped = CONTROL_CHARS.sub("", text)
    if len(stripped) > settings.prompt_max_chars:
        _log_security_event("over_length", stripped)
        raise PromptRejected()
    matched = any(pattern.search(stripped) for pattern in INJECTION_PATTERNS)
    if matched:
        _log_security_event("injection_signature", stripped)
        raise PromptRejected()
    return stripped
