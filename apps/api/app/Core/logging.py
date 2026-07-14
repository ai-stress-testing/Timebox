"""Structured JSON logging with trace_id propagation. No PII in logs — ever."""
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")

_SERVICE_NAME = "timebox-api"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": _SERVICE_NAME,
            "trace_id": trace_id_var.get(),
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
