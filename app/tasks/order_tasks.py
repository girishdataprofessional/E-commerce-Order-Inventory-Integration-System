"""
Order processing task — validates line items, locks inventory rows,
decrements stock, and logs every result to sync_logs.
"""

import logging
import time
import traceback
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.db.models import Order, OrderStatus, Inventory, SyncLog, SyncStatus, Product

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.order_tasks.process_order",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    queue="orders",
)
def process_order(self, order_id: int):
    """
    Process a single order:
    1. Mark as PROCESSING
    2. For each line item, look up SKU and lock inventory row
    3. Check stock and decrement
    4. Mark COMPLETED, write success log
    On failure: mark FAILED, optionally retry with backoff.
    """
    start_time = time.time()
    db: Session = SessionLocal()

    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return {"status": "error", "message": f"Order {order_id} not found"}

        logger.info(f"Processing order {order.external_order_id} (id={order_id}, items={len(order.items)})")

        order.status = OrderStatus.PROCESSING
        db.commit()

        # validate + update inventory with row-level locking
        for item in order.items:
            product = db.query(Product).filter(Product.sku == item.sku).first()
            if not product:
                raise ValueError(f"Product with SKU '{item.sku}' not found in catalog")

            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == product.id)
                .with_for_update()
                .first()
            )
            if not inventory:
                raise ValueError(f"No inventory record for '{item.sku}'")

            available = inventory.quantity - inventory.reserved
            if available < item.quantity:
                raise ValueError(
                    f"Insufficient stock for '{item.sku}': "
                    f"requested={item.quantity}, available={available}"
                )

            inventory.quantity -= item.quantity
            inventory.updated_at = datetime.now(timezone.utc)
            logger.info(f"  {item.sku} -= {item.quantity} (remaining: {inventory.quantity})")

        # done
        order.status = OrderStatus.COMPLETED
        order.processed_at = datetime.now(timezone.utc)
        order.error_message = None

        duration_ms = int((time.time() - start_time) * 1000)
        db.add(SyncLog(
            task_id=self.request.id,
            task_name="process_order",
            status=SyncStatus.SUCCESS,
            order_id=order.id,
            details=f"Order {order.external_order_id} processed — {len(order.items)} items fulfilled.",
            duration_ms=duration_ms,
        ))
        db.commit()

        logger.info(f"Order {order.external_order_id} completed in {duration_ms}ms")
        return {
            "status": "completed",
            "order_id": order_id,
            "external_order_id": order.external_order_id,
            "duration_ms": duration_ms,
        }

    except ValueError as e:
        # business logic errors — no retry
        db.rollback()
        _mark_failed(db, order_id, str(e), self.request.id, start_time)
        logger.warning(f"Order {order_id} failed (business): {e}")
        return {"status": "failed", "order_id": order_id, "error": str(e)}

    except Exception as e:
        # unexpected errors — retry with exponential backoff
        db.rollback()
        error_msg = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc()
        _mark_failed(db, order_id, error_msg, self.request.id, start_time, tb)
        logger.error(f"Order {order_id} failed: {error_msg}")

        if self.request.retries < self.max_retries:
            delay = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            logger.info(f"Retrying order {order_id} in {delay}s (attempt {self.request.retries + 1})")
            _log_retry(db, order_id, self.request.id, self.request.retries + 1, error_msg)
            raise self.retry(countdown=delay, exc=e)

        return {"status": "failed", "order_id": order_id, "error": error_msg}

    finally:
        db.close()


def _mark_failed(db, order_id, error_message, task_id, start_time, tb=None):
    """Set order status to FAILED and write a failure log."""
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = OrderStatus.FAILED
            order.error_message = error_message

        db.add(SyncLog(
            task_id=task_id,
            task_name="process_order",
            status=SyncStatus.FAILURE,
            order_id=order_id,
            error_message=error_message,
            traceback=tb,
            duration_ms=int((time.time() - start_time) * 1000),
        ))
        db.commit()
    except Exception as log_err:
        logger.error(f"Could not log failure: {log_err}")
        db.rollback()


def _log_retry(db, order_id, task_id, attempt, error):
    """Write a retry entry to sync_logs."""
    try:
        db.add(SyncLog(
            task_id=task_id,
            task_name="process_order",
            status=SyncStatus.RETRY,
            order_id=order_id,
            details=f"Retry attempt {attempt}",
            error_message=error,
        ))
        db.commit()
    except Exception as log_err:
        logger.error(f"Could not log retry: {log_err}")
        db.rollback()
