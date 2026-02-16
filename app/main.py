"""
FastAPI application — main entry point.
Sets up middleware, exception handling, and registers route modules.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import setup_logging, correlation_id_var, generate_correlation_id
from app.db.base import create_tables
from app.api import webhooks, orders, products, inventory, monitoring

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Fulfil ERP API...")
    create_tables()
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Fulfil ERP - Order Processing API",
    description="Async order processing with Celery workers, inventory management, and live monitoring.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Attach a correlation ID to every request for tracing."""
    cid = request.headers.get("X-Correlation-ID", generate_correlation_id())
    correlation_id_var.set(cid)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error."},
    )


# routes
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(orders.router, prefix="/api", tags=["Orders"])
app.include_router(products.router, prefix="/api", tags=["Products"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(monitoring.router, prefix="/api", tags=["Monitoring"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Fulfil ERP - Order Processing API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
