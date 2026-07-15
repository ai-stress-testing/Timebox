"""Vault schemas — the key file is identity + encryption root."""
from typing import Literal

from pydantic import Field

from app.Schemas.base import ApiModel, UtcDateTime


class Keyfile(ApiModel):
    format: Literal["timebox-keyfile"]
    version: Literal[1]
    user_id: str = Field(min_length=36, max_length=36)
    secret: str = Field(min_length=32, max_length=64)
    created_at: str


class VaultStatusResponse(ApiModel):
    registered: bool


class GenerateResponse(ApiModel):
    keyfile: Keyfile


class UnlockRequest(ApiModel):
    keyfile: Keyfile


class UnlockResponse(ApiModel):
    token: str
    user_id: str
    expires_at: UtcDateTime


class ResetRequest(ApiModel):
    confirm: Literal["ERASE"]
