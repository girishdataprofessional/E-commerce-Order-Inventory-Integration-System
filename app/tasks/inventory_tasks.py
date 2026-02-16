"""
Periodic inventory sync — runs via Celery Beat to check stock levels
and flag low/out-of-stock products.
"""

import logging
import time
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.orm import joinedload

from app.db.base import SessionLocal
from app.db.models import Inventory, SyncLog, SyncStatus
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@shared_task(
    name="app.tasks.inventory_tasks.sync_inventory",
    acks_late=True,
    queue="default",
)
def sync_inventory():
    """
    Scan all inventory records and log warnings for items that are
    below the reorder level or completely out of stock.
    """
    start_time = time.time()
    db = SessionLocal()

    try:
        logger.info("Starting inventory sync...")

        items = db.query(Inventory).options(joinedload(Inventory.product)).all()
        low_stock = []
        out_of_stock = []
        total = len(items)

        for inv in items:
            name = inv.product.name if inv.product else f"product_id={inv.product_id}"
            sku = inv.product.sku if inv.product else "?"
            available = inv.quantity - inv.reserved

            if available <= 0:
                out_of_stock.append({"sku": sku, "name": name, "available": available})
                logger.warning(f"OUT OF STOCK: {sku} ({name})")
            elif available <= inv.reorder_level:
                low_stock.append({
                    "sku": sku, "name": name,
                    "available": available, "reorder_level": inv.reorder_level,
                })
                logger.warning(f"LOW STOCK: {sku} ({name}) — {available} left, reorder at {inv.reorder_level}")

        duration_ms = int((time.time() - start_time) * 1000)

        summary = (
            f"Inventory sync done: {total} products checked, "
            f"{len(low_stock)} low stock, {len(out_of_stock)} out of stock."
        )
        logger.info(summary)

        # log per-alert entries
        for item in out_of_stock:
            db.add(SyncLog(
                task_name="sync_inventory",
                status=SyncStatus.FAILURE,
                details=f"OUT OF STOCK: {item['sku']} — {item['name']}",
                error_message=f"Available: {item['available']}",
                duration_ms=duration_ms,
            ))

        for item in low_stock:
            db.add(SyncLog(
                task_name="sync_inventory",
                status=SyncStatus.SUCCESS,
                details=(
                    f"LOW STOCK: {item['sku']} — {item['name']}, "
                    f"available={item['available']}, reorder_level={item['reorder_level']}"
                ),
                duration_ms=duration_ms,
            ))

        # overall sync log
        has_issues = len(low_stock) > 0 or len(out_of_stock) > 0
        db.add(SyncLog(
            task_name="sync_inventory",
            status=SyncStatus.SUCCESS if not has_issues else SyncStatus.SUCCESS,
            details=summary,
            duration_ms=duration_ms,
        ))

        db.commit()

        return {
            "status": "completed",
            "total_products": total,
            "low_stock": len(low_stock),
            "out_of_stock": len(out_of_stock),
            "duration_ms": duration_ms,
        }

    except Exception as e:
        db.rollback()
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Inventory sync failed: {e}", exc_info=True)

        try:
            db.add(SyncLog(
                task_name="sync_inventory",
                status=SyncStatus.FAILURE,
                error_message=str(e),
                duration_ms=duration_ms,
            ))
            db.commit()
        except Exception:
            db.rollback()

        return {"status": "failed", "error": str(e)}

    finally:
        db.close()
