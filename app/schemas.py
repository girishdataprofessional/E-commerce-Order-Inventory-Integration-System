"""
Pydantic v2 schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ─── Shopify Webhook Schemas ────────────────────────────

class ShopifyCustomer(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None


class ShopifyLineItem(BaseModel):
    sku: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    quantity: int = 1
    price: str = "0.00"
    variant_id: Optional[int] = None
    product_id: Optional[int] = None


class ShopifyOrderWebhook(BaseModel):
    """Incoming Shopify order webhook payload."""
    id: int
    order_number: Optional[int] = None
    email: Optional[str] = None
    total_price: str = "0.00"
    currency: str = "USD"
    customer: Optional[ShopifyCustomer] = None
    line_items: list[ShopifyLineItem] = []
    created_at: Optional[str] = None
    note: Optional[str] = None

    model_config = ConfigDict(extra="allow")


# ─── API Response Schemas ───────────────────────────────

class WebhookResponse(BaseModel):
    status: str
    message: str
    order_id: Optional[int] = None
    task_id: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    sku: str
    name: Optional[str] = None
    quantity: int
    unit_price: float
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    external_order_id: str
    status: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    total_amount: float
    currency: str
    source: str
    retry_count: int
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    items: list[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page: int
    page_size: int


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    reserved: int
    available: int
    reorder_level: int
    is_low_stock: bool
    warehouse_location: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncLogResponse(BaseModel):
    id: int
    task_id: Optional[str] = None
    task_name: str
    status: str
    order_id: Optional[int] = None
    details: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    total_orders: int
    completed_orders: int
    failed_orders: int
    pending_orders: int
    success_rate: float
    avg_processing_time_ms: Optional[float] = None
    orders_last_hour: int
    low_stock_alerts: int
    total_sync_logs: int
