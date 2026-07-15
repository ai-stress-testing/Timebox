"""Session auth middleware — bearer token → (user_id, data key) on request.state.
Everything is locked except the vault, health, and docs routes.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.Core.sessions import SessionStore

_OPEN_PATHS = frozenset(
    {
        "/health",
        "/api/v1/health",
        "/api/v1/vault/status",
        "/api/v1/vault/generate",
        "/api/v1/vault/unlock",
        "/docs",
        "/openapi.json",
    }
)


class SessionAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, store: SessionStore, api_prefix: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._store = store
        self._api_prefix = api_prefix

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        is_api_path = request.url.path.startswith(self._api_prefix)
        if (
            not is_api_path
            or request.url.path in _OPEN_PATHS
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
        header = request.headers.get("authorization", "")
        has_bearer = header.lower().startswith("bearer ")
        token = header[7:] if has_bearer else ""
        entry = self._store.resolve(token) if token else None
        if entry is None:
            return JSONResponse({"detail": "vault is locked"}, status_code=401)
        request.state.user_id = entry.user_id
        request.state.data_key = entry.data_key
        request.state.session_token = entry.token
        return await call_next(request)
