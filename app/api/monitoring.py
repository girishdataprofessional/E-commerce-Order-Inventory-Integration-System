"""
Monitoring & Health API — health checks, sync logs, and aggregate metrics.
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from app.db.base import get_db
from app.db.models import Order, OrderStatus, SyncLog, SyncStatus, Inventory
from app.schemas import HealthResponse, MetricsResponse, SyncLogResponse
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Deep health check — verifies database and Redis connectivity.
    """
    db_status = "disconnected"
    redis_status = "disconnected"

    # Check PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        import redis
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_status = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    overall = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/sync-logs", response_model=list[SyncLogResponse])
async def list_sync_logs(
    status: str = Query(None, description="Filter: success, failure, retry"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent sync/task logs with optional status filtering."""
    query = db.query(SyncLog)

    if status:
        try:
            status_enum = SyncStatus(status.lower())
            query = query.filter(SyncLog.status == status_enum)
        except ValueError:
            pass

    logs = query.order_by(desc(SyncLog.created_at)).limit(limit).all()

    return [
        SyncLogResponse(
            id=log.id,
            task_id=log.task_id,
            task_name=log.task_name,
            status=log.status.value if isinstance(log.status, SyncStatus) else log.status,
            order_id=log.order_id,
            details=log.details,
            error_message=log.error_message,
            duration_ms=log.duration_ms,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """Aggregate metrics for the ERP system — orders, success rate, processing times."""
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    # Order counts by status
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    completed = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.COMPLETED).scalar() or 0
    failed = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.FAILED).scalar() or 0
    pending = db.query(func.count(Order.id)).filter(
        Order.status.in_([OrderStatus.PENDING, OrderStatus.PROCESSING])
    ).scalar() or 0

    # Success rate
    success_rate = (completed / total_orders * 100) if total_orders > 0 else 0.0

    # Orders in last hour
    orders_last_hour = (
        db.query(func.count(Order.id))
        .filter(Order.created_at >= one_hour_ago)
        .scalar() or 0
    )

    # Average processing time from sync logs
    avg_time = (
        db.query(func.avg(SyncLog.duration_ms))
        .filter(SyncLog.status == SyncStatus.SUCCESS)
        .scalar()
    )

    # Low stock alerts count
    all_inventory = db.query(Inventory).all()
    low_stock_count = sum(1 for inv in all_inventory if inv.is_low_stock)

    # Total sync logs
    total_logs = db.query(func.count(SyncLog.id)).scalar() or 0

    return MetricsResponse(
        total_orders=total_orders,
        completed_orders=completed,
        failed_orders=failed,
        pending_orders=pending,
        success_rate=round(success_rate, 2),
        avg_processing_time_ms=round(avg_time, 2) if avg_time else None,
        orders_last_hour=orders_last_hour,
        low_stock_alerts=low_stock_count,
        total_sync_logs=total_logs,
    )
