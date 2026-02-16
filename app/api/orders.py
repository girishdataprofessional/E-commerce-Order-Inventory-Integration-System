"""
Orders REST API — list, detail, and retry operations.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.base import get_db
from app.db.models import Order, OrderStatus
from app.schemas import OrderResponse, OrderListResponse, WebhookResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    status: str = Query(None, description="Filter by status: pending, processing, completed, failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all orders with pagination and optional status filter."""
    query = db.query(Order).options(joinedload(Order.items))

    if status:
        try:
            status_enum = OrderStatus(status.lower())
            query = query.filter(Order.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    total = query.count()
    orders = (
        query.order_by(desc(Order.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Manually build response to handle the line_total property
    order_responses = []
    for order in orders:
        items = [
            {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.quantity * item.unit_price,
            }
            for item in order.items
        ]
        order_responses.append(
            OrderResponse(
                id=order.id,
                external_order_id=order.external_order_id,
                status=order.status.value if isinstance(order.status, OrderStatus) else order.status,
                customer_name=order.customer_name,
                customer_email=order.customer_email,
                total_amount=order.total_amount,
                currency=order.currency,
                source=order.source,
                retry_count=order.retry_count,
                error_message=order.error_message,
                processed_at=order.processed_at,
                created_at=order.created_at,
                items=items,
            )
        )

    return OrderListResponse(
        orders=order_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a single order with its line items."""
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    items = [
        {
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": item.quantity * item.unit_price,
        }
        for item in order.items
    ]

    return OrderResponse(
        id=order.id,
        external_order_id=order.external_order_id,
        status=order.status.value if isinstance(order.status, OrderStatus) else order.status,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        total_amount=order.total_amount,
        currency=order.currency,
        source=order.source,
        retry_count=order.retry_count,
        error_message=order.error_message,
        processed_at=order.processed_at,
        created_at=order.created_at,
        items=items,
    )


@router.post("/orders/{order_id}/retry", response_model=WebhookResponse)
async def retry_order(order_id: int, db: Session = Depends(get_db)):
    """Manually retry a failed order by re-dispatching the Celery task."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order.status not in (OrderStatus.FAILED, OrderStatus.PENDING):
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed or pending orders. Current status: {order.status.value}",
        )

    # Reset order status
    order.status = OrderStatus.PENDING
    order.error_message = None
    order.retry_count += 1
    db.commit()

    # Re-dispatch Celery task
    task_id = None
    try:
        from app.tasks.order_tasks import process_order
        result = process_order.delay(order.id)
        task_id = result.id
        logger.info(f"Retrying order {order_id}, task_id={task_id}")
    except Exception as e:
        logger.error(f"Failed to dispatch retry task for order {order_id}: {e}")

    return WebhookResponse(
        status="retrying",
        message=f"Order {order_id} has been re-queued for processing (retry #{order.retry_count}).",
        order_id=order.id,
        task_id=task_id,
    )
