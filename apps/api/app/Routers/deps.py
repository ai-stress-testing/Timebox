"""Router dependencies — session context injected by the auth middleware."""
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class SessionContext:
    user_id: str
    data_key: bytes
    token: str


def get_session_context(request: Request) -> SessionContext:
    return SessionContext(
        user_id=request.state.user_id,
        data_key=request.state.data_key,
        token=request.state.session_token,
    )
