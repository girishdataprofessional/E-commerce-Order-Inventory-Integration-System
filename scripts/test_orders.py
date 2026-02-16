"""
Integration test script — sends multiple test orders via the webhook endpoint.
Includes both success and failure scenarios.

Usage:
    python scripts/test_orders.py
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ─── Test Orders ────────────────────────────────────

TEST_ORDERS = [
    {
        "name": "Standard electronics order",
        "payload": {
            "id": 90001,
            "email": "alice@example.com",
            "total_price": "1149.98",
            "currency": "USD",
            "customer": {"first_name": "Alice", "last_name": "Johnson"},
            "line_items": [
                {"sku": "LAPTOP-001", "title": "ProBook 15 Laptop", "quantity": 1, "price": "899.99"},
                {"sku": "EARBUDS-001", "title": "SoundPods Pro", "quantity": 1, "price": "149.99"},
            ],
        },
    },
    {
        "name": "Clothing bulk order",
        "payload": {
            "id": 90002,
            "email": "bob@example.com",
            "total_price": "214.96",
            "currency": "USD",
            "customer": {"first_name": "Bob", "last_name": "Smith"},
            "line_items": [
                {"sku": "TSHIRT-001", "title": "Essential Cotton Tee", "quantity": 3, "price": "24.99"},
                {"sku": "JEANS-001", "title": "Classic Slim Jeans", "quantity": 2, "price": "59.99"},
                {"sku": "CAP-001", "title": "Snapback Logo Cap", "quantity": 1, "price": "19.99"},
            ],
        },
    },
    {
        "name": "Kitchen essentials",
        "payload": {
            "id": 90003,
            "email": "carol@example.com",
            "total_price": "144.97",
            "currency": "USD",
            "customer": {"first_name": "Carol", "last_name": "Williams"},
            "line_items": [
                {"sku": "COFFEE-001", "title": "BrewMaster 3000", "quantity": 1, "price": "79.99"},
                {"sku": "MUG-001", "title": "Ceramic Travel Mug", "quantity": 2, "price": "14.99"},
                {"sku": "LAMP-001", "title": "Nordic Desk Lamp", "quantity": 1, "price": "34.99"},
            ],
        },
    },
    {
        "name": "Fitness bundle",
        "payload": {
            "id": 90004,
            "email": "dave@example.com",
            "total_price": "219.97",
            "currency": "USD",
            "customer": {"first_name": "Dave", "last_name": "Brown"},
            "line_items": [
                {"sku": "YOGA-001", "title": "ProFlex Yoga Mat", "quantity": 1, "price": "39.99"},
                {"sku": "DUMBBELL-001", "title": "Adjustable Dumbbell Set", "quantity": 1, "price": "149.99"},
                {"sku": "BOTTLE-001", "title": "HydroFlask 32oz", "quantity": 1, "price": "29.99"},
            ],
        },
    },
    {
        "name": "FAILURE: Non-existent SKU",
        "payload": {
            "id": 90005,
            "email": "error@example.com",
            "total_price": "99.99",
            "currency": "USD",
            "customer": {"first_name": "Error", "last_name": "Test"},
            "line_items": [
                {"sku": "NONEXISTENT-SKU", "title": "Ghost Product", "quantity": 1, "price": "99.99"},
            ],
        },
    },
    {
        "name": "High-value tech order",
        "payload": {
            "id": 90006,
            "email": "eve@example.com",
            "total_price": "1399.97",
            "currency": "USD",
            "customer": {"first_name": "Eve", "last_name": "Davis"},
            "line_items": [
                {"sku": "PHONE-001", "title": "SmartPhone X12 Pro", "quantity": 1, "price": "699.99"},
                {"sku": "TABLET-001", "title": "DigiPad Air 10", "quantity": 1, "price": "449.99"},
                {"sku": "WATCH-001", "title": "FitWatch Ultra", "quantity": 1, "price": "249.99"},
            ],
        },
    },
]


def send_test_orders():
    """Send all test orders to the webhook endpoint."""
    client = httpx.Client(base_url=API_BASE, timeout=10.0)

    print("=" * 60)
    print("🧪 Fulfil ERP — Integration Test: Sending Test Orders")
    print("=" * 60)
    print(f"   API Base URL: {API_BASE}")
    print()

    # Check API health first
    try:
        health = client.get("/api/health")
        health_data = health.json()
        print(f"  Health: {health_data.get('status', 'unknown')}")
        print(f"  DB: {health_data.get('database', 'unknown')}")
        print(f"  Redis: {health_data.get('redis', 'unknown')}")
    except Exception as e:
        print(f"  ❌ API not reachable: {e}")
        print("  Make sure docker-compose is running!")
        return

    print()
    print("-" * 60)

    for i, test in enumerate(TEST_ORDERS, 1):
        print(f"\n[{i}/{len(TEST_ORDERS)}] {test['name']}")
        try:
            response = client.post(
                "/webhooks/shopify/orders",
                json=test["payload"],
            )
            data = response.json()
            status_emoji = "✅" if response.status_code == 202 else "⚠️"
            print(f"  {status_emoji} Status: {response.status_code}")
            print(f"     Response: {data.get('status', 'unknown')} — {data.get('message', '')}")
            if data.get("task_id"):
                print(f"     Task ID: {data['task_id']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        time.sleep(0.5)  # Small delay between orders

    print("\n" + "=" * 60)
    print("⏳ Waiting 5 seconds for Celery to process orders...")
    time.sleep(5)

    # Check results
    print("\n📊 Results:")
    try:
        metrics = client.get("/api/metrics").json()
        print(f"  Total Orders: {metrics.get('total_orders', 0)}")
        print(f"  Completed: {metrics.get('completed_orders', 0)}")
        print(f"  Failed: {metrics.get('failed_orders', 0)}")
        print(f"  Pending: {metrics.get('pending_orders', 0)}")
        print(f"  Success Rate: {metrics.get('success_rate', 0)}%")
    except Exception as e:
        print(f"  ❌ Could not fetch metrics: {e}")

    print("\n✨ Done! Check the dashboard at http://localhost:8501")
    client.close()


if __name__ == "__main__":
    send_test_orders()
