"""
Structured JSON logging with correlation ID support.
"""

import logging
import uuid
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# per-request correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_correlation_id() -> str:
    return str(uuid.uuid4())


class CorrelationFilter(logging.Filter):
    """Injects the current correlation_id into every log record."""
    def filter(self, record):
        record.correlation_id = correlation_id_var.get("")
        return True


def setup_logging(level: str = "INFO"):
    fmt = "%(asctime)s %(name)s %(levelname)s %(correlation_id)s %(message)s"
    formatter = jsonlogger.JsonFormatter(fmt)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers = [handler]

    # quiet down noisy libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
