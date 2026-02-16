"""
Shopify webhook — receives order payloads, persists them,
and dispatches Celery tasks for async processing.
"""

import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Order, OrderItem, OrderStatus, Product
from app.schemas import ShopifyOrderWebhook, WebhookResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/shopify/orders", response_model=WebhookResponse, status_code=202)
async def receive_shopify_order(
    payload: ShopifyOrderWebhook,
    request: Request,
    db: Session = Depends(get_db),
):
    """Accept a Shopify-format order webhook, store it, and queue processing."""
    external_id = str(payload.id)
    logger.info(f"Received order webhook: {external_id}")

    # idempotency — skip if we already have this order
    existing = db.query(Order).filter(Order.external_order_id == external_id).first()
    if existing:
        logger.warning(f"Duplicate webhook for order {external_id}")
        return WebhookResponse(
            status="duplicate",
            message=f"Order {external_id} already exists.",
            order_id=existing.id,
        )

    # build customer info
    customer_name = None
    customer_email = payload.email
    if payload.customer:
        parts = [payload.customer.first_name or "", payload.customer.last_name or ""]
        customer_name = " ".join(p for p in parts if p).strip() or None
        if not customer_email and payload.customer.email:
            customer_email = payload.customer.email

    # persist order
    order = Order(
        external_order_id=external_id,
        status=OrderStatus.PENDING,
        customer_name=customer_name,
        customer_email=customer_email,
        total_amount=float(payload.total_price),
        currency=payload.currency,
        source="shopify",
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(order)
    db.flush()

    # line items
    for item in payload.line_items:
        sku = item.sku or f"UNKNOWN-{item.variant_id or item.product_id or 'N/A'}"
        product = db.query(Product).filter(Product.sku == sku).first()

        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id if product else None,
            sku=sku,
            name=item.title or item.name,
            quantity=item.quantity,
            unit_price=float(item.price),
        ))

    db.commit()
    db.refresh(order)
    logger.info(f"Order {external_id} saved (id={order.id}, {len(payload.line_items)} items)")

    # dispatch celery task
    task_id = None
    try:
        from app.tasks.order_tasks import process_order
        result = process_order.delay(order.id)
        task_id = result.id
        logger.info(f"Dispatched task {task_id} for order {order.id}")
    except Exception as e:
        logger.error(f"Could not dispatch task for order {order.id}: {e}")

    return WebhookResponse(
        status="accepted",
        message=f"Order {external_id} queued for processing.",
        order_id=order.id,
        task_id=task_id,
    )
