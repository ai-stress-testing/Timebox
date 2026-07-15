"""AI timebox schemas — local LLM runtimes only, prompts never persisted."""
from typing import Literal

from pydantic import Field, model_validator

from app.Schemas.base import ApiModel, UtcDateTime

ProviderKindField = Literal["ollama", "openai_compat"]


class AiHealthResponse(ApiModel):
    ok: bool
    model: str
    base_url: str
    detail: str | None


class LlmSettingsIn(ApiModel):
    provider_kind: ProviderKindField
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    # None = leave the stored key unchanged; "" = clear it; anything else = set it.
    api_key: str | None = Field(default=None, max_length=500)


class LlmSettingsOut(ApiModel):
    provider_kind: ProviderKindField
    base_url: str
    model: str
    has_api_key: bool


class TimeboxRequest(ApiModel):
    task_title: str = Field(min_length=1, max_length=300)
    estimated_minutes: int = Field(gt=0, le=24 * 60)
    window_start: UtcDateTime
    window_end: UtcDateTime
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_window(self) -> "TimeboxRequest":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class SlotProposal(ApiModel):
    start_at: UtcDateTime
    end_at: UtcDateTime
    rationale: str


class TimeboxResponse(ApiModel):
    proposal: SlotProposal
    ai_session_id: str
