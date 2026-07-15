"""Trace ID middleware — every request gets a trace_id on logs + response header."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.Core.ids import uuid7
from app.Core.logging import trace_id_var


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        trace_id = request.headers.get("x-trace-id") or uuid7()
        trace_id_var.set(trace_id)
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response
