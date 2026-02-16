"""Initial schema - create all tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sku', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_products_sku', 'products', ['sku'])
    op.create_index('ix_products_id', 'products', ['id'])

    # Inventory table
    op.create_table(
        'inventory',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, unique=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reserved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reorder_level', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('warehouse_location', sa.String(50), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_inventory_id', 'inventory', ['id'])

    # Orders table
    orderstatus_enum = sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', name='orderstatus')
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_order_id', sa.String(100), nullable=False, unique=True),
        sa.Column('status', orderstatus_enum, nullable=False, server_default='pending'),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('source', sa.String(50), server_default='shopify'),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('ix_orders_external_order_id', 'orders', ['external_order_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_status_created', 'orders', ['status', 'created_at'])

    # Order items table
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('sku', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Float(), nullable=False, server_default='0.0'),
    )
    op.create_index('ix_order_items_id', 'order_items', ['id'])

    # Sync logs table
    syncstatus_enum = sa.Enum('success', 'failure', 'retry', name='syncstatus')
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('task_name', sa.String(100), nullable=False),
        sa.Column('status', syncstatus_enum, nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_sync_logs_id', 'sync_logs', ['id'])
    op.create_index('ix_sync_logs_task_id', 'sync_logs', ['task_id'])
    op.create_index('ix_sync_logs_status', 'sync_logs', ['status'])
    op.create_index('ix_sync_logs_status_created', 'sync_logs', ['status', 'created_at'])


def downgrade() -> None:
    op.drop_table('sync_logs')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('inventory')
    op.drop_table('products')
    sa.Enum(name='orderstatus').drop(op.get_bind())
    sa.Enum(name='syncstatus').drop(op.get_bind())
