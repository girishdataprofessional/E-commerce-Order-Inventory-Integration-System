"""
Database seed script — populates the ERP with sample products and inventory.
Idempotent: safe to run multiple times.

Usage:
    python scripts/seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal, create_tables
from app.db.models import Product, Inventory


SEED_PRODUCTS = [
    # Electronics
    {"sku": "LAPTOP-001", "name": "ProBook 15 Laptop", "price": 899.99, "category": "Electronics", "description": "15.6\" Full HD, Intel i7, 16GB RAM, 512GB SSD"},
    {"sku": "PHONE-001", "name": "SmartPhone X12 Pro", "price": 699.99, "category": "Electronics", "description": "6.7\" AMOLED, 128GB, 5G capable"},
    {"sku": "TABLET-001", "name": "DigiPad Air 10", "price": 449.99, "category": "Electronics", "description": "10.9\" display, M1 chip, 256GB"},
    {"sku": "WATCH-001", "name": "FitWatch Ultra", "price": 249.99, "category": "Electronics", "description": "GPS, heart rate, 7-day battery"},
    {"sku": "EARBUDS-001", "name": "SoundPods Pro", "price": 149.99, "category": "Electronics", "description": "Active noise cancellation, 24hr battery"},
    
    # Clothing
    {"sku": "TSHIRT-001", "name": "Essential Cotton Tee", "price": 24.99, "category": "Clothing", "description": "100% organic cotton, unisex fit"},
    {"sku": "JEANS-001", "name": "Classic Slim Jeans", "price": 59.99, "category": "Clothing", "description": "Stretch denim, mid-rise, slim fit"},
    {"sku": "JACKET-001", "name": "Urban Bomber Jacket", "price": 89.99, "category": "Clothing", "description": "Water-resistant, lightweight, zip-up"},
    {"sku": "SNEAKER-001", "name": "CloudStep Runners", "price": 119.99, "category": "Clothing", "description": "Memory foam sole, breathable mesh"},
    {"sku": "CAP-001", "name": "Snapback Logo Cap", "price": 19.99, "category": "Clothing", "description": "Adjustable, embroidered logo"},

    # Home & Kitchen
    {"sku": "COFFEE-001", "name": "BrewMaster 3000", "price": 79.99, "category": "Home & Kitchen", "description": "Programmable 12-cup coffee maker"},
    {"sku": "BLENDER-001", "name": "TurboBlend Pro", "price": 49.99, "category": "Home & Kitchen", "description": "1000W, 5-speed, BPA-free"},
    {"sku": "LAMP-001", "name": "Nordic Desk Lamp", "price": 34.99, "category": "Home & Kitchen", "description": "LED, dimmable, USB charging port"},
    {"sku": "PILLOW-001", "name": "DreamCloud Memory Pillow", "price": 29.99, "category": "Home & Kitchen", "description": "Cooling gel memory foam, queen size"},
    {"sku": "MUG-001", "name": "Ceramic Travel Mug", "price": 14.99, "category": "Home & Kitchen", "description": "16oz, insulated, spill-proof lid"},

    # Sports & Outdoors
    {"sku": "YOGA-001", "name": "ProFlex Yoga Mat", "price": 39.99, "category": "Sports", "description": "6mm thick, non-slip, eco-friendly"},
    {"sku": "BOTTLE-001", "name": "HydroFlask 32oz", "price": 29.99, "category": "Sports", "description": "Vacuum insulated, keeps cold 24hrs"},
    {"sku": "DUMBBELL-001", "name": "Adjustable Dumbbell Set", "price": 149.99, "category": "Sports", "description": "5-52.5 lbs, quick-change weight"},
    {"sku": "BACKPACK-001", "name": "TrailBlazer 40L Pack", "price": 69.99, "category": "Sports", "description": "Waterproof, ventilated back panel"},
    {"sku": "TENT-001", "name": "QuickPitch 2P Tent", "price": 129.99, "category": "Sports", "description": "2-person, 3-season, pop-up design"},
]

# Inventory quantities — some purposely low to trigger alerts
INVENTORY_LEVELS = {
    "LAPTOP-001": {"qty": 45, "reserved": 3, "reorder": 10, "location": "WH-A1"},
    "PHONE-001": {"qty": 120, "reserved": 8, "reorder": 20, "location": "WH-A2"},
    "TABLET-001": {"qty": 30, "reserved": 2, "reorder": 10, "location": "WH-A2"},
    "WATCH-001": {"qty": 8, "reserved": 0, "reorder": 15, "location": "WH-A3"},     # LOW STOCK
    "EARBUDS-001": {"qty": 200, "reserved": 15, "reorder": 25, "location": "WH-A3"},
    "TSHIRT-001": {"qty": 500, "reserved": 20, "reorder": 50, "location": "WH-B1"},
    "JEANS-001": {"qty": 3, "reserved": 1, "reorder": 10, "location": "WH-B1"},     # LOW STOCK
    "JACKET-001": {"qty": 60, "reserved": 5, "reorder": 10, "location": "WH-B2"},
    "SNEAKER-001": {"qty": 75, "reserved": 0, "reorder": 15, "location": "WH-B2"},
    "CAP-001": {"qty": 150, "reserved": 10, "reorder": 20, "location": "WH-B3"},
    "COFFEE-001": {"qty": 40, "reserved": 2, "reorder": 8, "location": "WH-C1"},
    "BLENDER-001": {"qty": 5, "reserved": 3, "reorder": 10, "location": "WH-C1"},   # LOW STOCK
    "LAMP-001": {"qty": 90, "reserved": 0, "reorder": 15, "location": "WH-C2"},
    "PILLOW-001": {"qty": 0, "reserved": 0, "reorder": 10, "location": "WH-C2"},    # OUT OF STOCK
    "MUG-001": {"qty": 300, "reserved": 25, "reorder": 30, "location": "WH-C3"},
    "YOGA-001": {"qty": 55, "reserved": 0, "reorder": 10, "location": "WH-D1"},
    "BOTTLE-001": {"qty": 180, "reserved": 12, "reorder": 20, "location": "WH-D1"},
    "DUMBBELL-001": {"qty": 22, "reserved": 0, "reorder": 5, "location": "WH-D2"},
    "BACKPACK-001": {"qty": 7, "reserved": 2, "reorder": 10, "location": "WH-D2"},  # LOW STOCK
    "TENT-001": {"qty": 15, "reserved": 1, "reorder": 5, "location": "WH-D3"},
}


def seed():
    """Seed the database with sample products and inventory."""
    db = SessionLocal()
    
    try:
        created = 0
        skipped = 0

        for product_data in SEED_PRODUCTS:
            # Check if product already exists
            existing = db.query(Product).filter(Product.sku == product_data["sku"]).first()
            if existing:
                skipped += 1
                continue

            # Create product
            product = Product(**product_data)
            db.add(product)
            db.flush()

            # Create inventory record
            inv_data = INVENTORY_LEVELS.get(product_data["sku"], {})
            inventory = Inventory(
                product_id=product.id,
                quantity=inv_data.get("qty", 50),
                reserved=inv_data.get("reserved", 0),
                reorder_level=inv_data.get("reorder", 10),
                warehouse_location=inv_data.get("location", "WH-X1"),
            )
            db.add(inventory)
            created += 1

        db.commit()
        print(f"✅ Seed complete: {created} products created, {skipped} skipped (already exist)")
        
        # Summary
        total = db.query(Product).count()
        low_stock = sum(
            1 for inv in db.query(Inventory).all()
            if inv.is_low_stock
        )
        print(f"   Total products: {total}")
        print(f"   Low stock alerts: {low_stock}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding Fulfil ERP database...")
    create_tables()
    seed()
