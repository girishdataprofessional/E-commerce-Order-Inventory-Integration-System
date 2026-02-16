"""
ORM models — Product, Inventory, Order, OrderItem, SyncLog.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON,
    Enum, ForeignKey, Index, Boolean,
)
from sqlalchemy.orm import relationship
from app.db.base import Base




class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"




class Product(Base):
    """Product catalog for the ERP system."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    category = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(sku='{self.sku}', name='{self.name}')>"


class Inventory(Base):
    """Real-time inventory tracking per product."""
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    reserved = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    warehouse_location = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="inventory")

    @property
    def available(self) -> int:
        """Available stock = total quantity - reserved."""
        return self.quantity - self.reserved

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is at or below reorder level."""
        return self.available <= self.reorder_level

    def __repr__(self):
        return f"<Inventory(product_id={self.product_id}, qty={self.quantity}, reserved={self.reserved})>"


class Order(Base):
    """Orders received from external sources (e.g., Shopify webhooks)."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    external_order_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), default="USD")
    source = Column(String(50), default="shopify")
    raw_payload = Column(JSON, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="order")

    # Indexes
    __table_args__ = (
        Index("ix_orders_status_created", "status", "created_at"),
    )

    def __repr__(self):
        return f"<Order(external_id='{self.external_order_id}', status='{self.status}')>"


class OrderItem(Base):
    """Individual line items within an order."""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    sku = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0.0)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    @property
    def line_total(self) -> float:
        return self.quantity * self.unit_price

    def __repr__(self):
        return f"<OrderItem(sku='{self.sku}', qty={self.quantity})>"


class SyncLog(Base):
    """Audit log for all async task executions (success, failure, retry)."""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), nullable=True, index=True)
    task_name = Column(String(100), nullable=False)
    status = Column(Enum(SyncStatus), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    order = relationship("Order", back_populates="sync_logs")

    # Indexes
    __table_args__ = (
        Index("ix_sync_logs_status_created", "status", "created_at"),
    )

    def __repr__(self):
        return f"<SyncLog(task='{self.task_name}', status='{self.status}')>"
