"""
Products REST API — list and detail operations.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.base import get_db
from app.db.models import Product
from app.schemas import ProductResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    category: str = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only show active products"),
    db: Session = Depends(get_db),
):
    """List all products with optional category filter."""
    query = db.query(Product)

    if active_only:
        query = query.filter(Product.is_active == True)

    if category:
        query = query.filter(Product.category == category)

    products = query.order_by(Product.name).all()
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return ProductResponse.model_validate(product)
