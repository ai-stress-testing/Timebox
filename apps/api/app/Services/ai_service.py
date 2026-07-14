"""AI timeboxing — Ollama proposes a slot; deterministic fallback if the model
output is unparseable. Prompt privacy: only SHA-256 hashes are persisted.
"""
import json
import time
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.Core import crypto
from app.Core.patterns import JSON_OBJECT
from app.Middleware.prompt_sanitiser import sanitise_prompt
from app.Models.ai import AiSession
from app.Repositories import ai_repo, event_repo
from app.Schemas.ai import SlotProposal, TimeboxRequest, TimeboxResponse
from app.Schemas.base import _to_naive_utc
from app.Services.Llm.base import ChatMessage, LlmProvider, LlmUnavailableError

_SYSTEM_PROMPT = (
    "You are Timebox's scheduling assistant. Given a task and a list of busy "
    "intervals (UTC), pick the best free slot inside the window. Prefer morning "
    "focus time, leave 15-minute buffers around busy intervals, and never "
    "overlap them. Respond with ONLY a JSON object: "
    '{"start_at": "<iso>", "end_at": "<iso>", "rationale": "<one sentence>"}'
)


class AiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _build_user_message(payload: TimeboxRequest, busy: list[tuple[str, str]]) -> str:
    structured = {
        "task": payload.task_title,
        "estimated_minutes": payload.estimated_minutes,
        "window_start": payload.window_start.isoformat() + "Z",
        "window_end": payload.window_end.isoformat() + "Z",
        "notes": payload.notes or "",
        "busy_intervals": [{"start": s, "end": e} for s, e in busy],
    }
    return json.dumps(structured)


def _parse_proposal(raw: str, payload: TimeboxRequest) -> SlotProposal | None:
    match = JSON_OBJECT.search(raw)
    if match is None:
        return None
    try:
        body = json.loads(match.group(0))
        start_at = _to_naive_utc(str(body["start_at"]))
        end_at = _to_naive_utc(str(body["end_at"]))
        rationale = str(body.get("rationale", "proposed by model"))[:500]
    except Exception:
        return None
    is_datetime = isinstance(start_at, datetime) and isinstance(end_at, datetime)
    if not is_datetime:
        return None
    in_window = payload.window_start <= start_at and end_at <= payload.window_end
    if not in_window or end_at <= start_at:
        return None
    return SlotProposal(start_at=start_at, end_at=end_at, rationale=rationale)


def _fallback_proposal(
    payload: TimeboxRequest, busy: list[tuple[datetime, datetime]]
) -> SlotProposal:
    duration = timedelta(minutes=payload.estimated_minutes)
    cursor = payload.window_start
    for interval_start, interval_end in sorted(busy):
        fits_before = cursor + duration <= interval_start
        if fits_before:
            break
        cursor = max(cursor, interval_end)
    if cursor + duration > payload.window_end:
        raise AiError(409, "no free slot of that length inside the window")
    return SlotProposal(
        start_at=cursor,
        end_at=cursor + duration,
        rationale="fallback: first free slot in the window (model output unusable)",
    )


async def propose_timebox(
    session: AsyncSession, user_id: str, provider: LlmProvider, payload: TimeboxRequest
) -> TimeboxResponse:
    clean_title = sanitise_prompt(payload.task_title)
    clean_notes = sanitise_prompt(payload.notes) if payload.notes else None
    events = await event_repo.list_in_range(
        session, user_id, payload.window_start, payload.window_end
    )
    busy_pairs = [(e.start_at, e.end_at) for e in events]
    busy_iso = [(s.isoformat() + "Z", e.isoformat() + "Z") for s, e in busy_pairs]
    clean_payload = payload.model_copy(update={"task_title": clean_title, "notes": clean_notes})
    user_message = _build_user_message(clean_payload, busy_iso)
    messages = (
        ChatMessage(role="system", content=_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_message),
    )
    started = time.monotonic()
    try:
        raw = await provider.chat(messages)
    except LlmUnavailableError as exc:
        raise AiError(503, f"AI unavailable: {exc}") from exc
    duration_ms = round((time.monotonic() - started) * 1000)
    proposal = _parse_proposal(raw, clean_payload) or _fallback_proposal(
        clean_payload, busy_pairs
    )
    ai_session = AiSession(
        user_id=user_id,
        kind="timebox",
        prompt_hash=crypto.sha256_hex(user_message),
        model=provider.model,
        duration_ms=duration_ms,
    )
    ai_repo.add_ai_session(session, ai_session)
    await session.commit()
    return TimeboxResponse(proposal=proposal, ai_session_id=ai_session.id)
