"""
Inventory REST API — stock levels and low-stock alerts.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db.base import get_db
from app.db.models import Inventory, Product
from app.schemas import InventoryResponse
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_inventory_response(inv: Inventory) -> InventoryResponse:
    """Build an InventoryResponse from an Inventory ORM instance."""
    return InventoryResponse(
        id=inv.id,
        product_id=inv.product_id,
        product_name=inv.product.name if inv.product else None,
        product_sku=inv.product.sku if inv.product else None,
        quantity=inv.quantity,
        reserved=inv.reserved,
        available=inv.available,
        reorder_level=inv.reorder_level,
        is_low_stock=inv.is_low_stock,
        warehouse_location=inv.warehouse_location,
        updated_at=inv.updated_at,
    )


@router.get("/inventory", response_model=list[InventoryResponse])
async def list_inventory(db: Session = Depends(get_db)):
    """List current inventory levels for all products."""
    items = (
        db.query(Inventory)
        .options(joinedload(Inventory.product))
        .order_by(Inventory.product_id)
        .all()
    )
    return [_build_inventory_response(inv) for inv in items]


@router.get("/inventory/alerts", response_model=list[InventoryResponse])
async def inventory_alerts(db: Session = Depends(get_db)):
    """List products with low stock (at or below reorder level)."""
    settings = get_settings()
    items = (
        db.query(Inventory)
        .options(joinedload(Inventory.product))
        .all()
    )
    low_stock = [inv for inv in items if inv.is_low_stock]
    logger.info(f"Low stock alerts: {len(low_stock)} products below reorder level")
    return [_build_inventory_response(inv) for inv in low_stock]
