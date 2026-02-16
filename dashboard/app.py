"""
Fulfil ERP Monitoring Dashboard
Streamlit + Plotly for real-time order and inventory monitoring.

Runs in two modes:
- Live: connects to PostgreSQL when DATABASE_URL is set
- Demo: generates sample data for standalone previews
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")


# -- Page setup ---------------------------------------------------------------

st.set_page_config(
    page_title="Fulfil ERP Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }

    .kpi-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #16192b 100%);
        border: 1px solid #2d3348;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); }
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
    }
    .kpi-green  { color: #64ffda; }
    .kpi-blue   { color: #82aaff; }
    .kpi-orange { color: #ffcb6b; }
    .kpi-red    { color: #ff5370; }
    .kpi-purple { color: #c792ea; }

    .status-badge {
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-completed  { background: #1a3a2a; color: #64ffda; border: 1px solid #2d6b4f; }
    .badge-pending    { background: #3a3520; color: #ffcb6b; border: 1px solid #6b5f2d; }
    .badge-processing { background: #1a2a3a; color: #82aaff; border: 1px solid #2d4f6b; }
    .badge-failed     { background: #3a1a20; color: #ff5370; border: 1px solid #6b2d3a; }

    .health-dot {
        display: inline-block;
        width: 12px; height: 12px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    .health-green { background: #64ffda; box-shadow: 0 0 8px #64ffda40; }
    .health-red   { background: #ff5370; box-shadow: 0 0 8px #ff537040; }
    @keyframes pulse {
        0%   { opacity: 1;   }
        50%  { opacity: 0.5; }
        100% { opacity: 1;   }
    }

    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ccd6f6;
        border-bottom: 2px solid #2d3348;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    [data-testid="stSidebar"] { background-color: #0a0d14; }
</style>
""", unsafe_allow_html=True)


# -- Demo data generators -----------------------------------------------------

def _generate_demo_data():
    """Build realistic-looking sample data for standalone demo."""
    now = datetime.now(timezone.utc)

    products = [
        ("LAPTOP-001", "ProBook 15 Laptop", 899.99, "Electronics"),
        ("PHONE-001", "SmartPhone X12 Pro", 699.99, "Electronics"),
        ("TABLET-001", "DigiPad Air 10", 449.99, "Electronics"),
        ("WATCH-001", "FitWatch Ultra", 249.99, "Electronics"),
        ("EARBUDS-001", "SoundPods Pro", 149.99, "Electronics"),
        ("TSHIRT-001", "Essential Cotton Tee", 24.99, "Clothing"),
        ("JEANS-001", "Classic Slim Jeans", 59.99, "Clothing"),
        ("JACKET-001", "Urban Bomber Jacket", 89.99, "Clothing"),
        ("SNEAKER-001", "CloudStep Runners", 119.99, "Clothing"),
        ("CAP-001", "Snapback Logo Cap", 19.99, "Clothing"),
        ("COFFEE-001", "BrewMaster 3000", 79.99, "Home & Kitchen"),
        ("BLENDER-001", "TurboBlend Pro", 49.99, "Home & Kitchen"),
        ("LAMP-001", "Nordic Desk Lamp", 34.99, "Home & Kitchen"),
        ("PILLOW-001", "DreamCloud Pillow", 29.99, "Home & Kitchen"),
        ("MUG-001", "Ceramic Travel Mug", 14.99, "Home & Kitchen"),
        ("YOGA-001", "ProFlex Yoga Mat", 39.99, "Sports"),
        ("BOTTLE-001", "HydroFlask 32oz", 29.99, "Sports"),
        ("DUMBBELL-001", "Adjustable Dumbbell", 149.99, "Sports"),
        ("BACKPACK-001", "TrailBlazer 40L", 69.99, "Sports"),
        ("TENT-001", "QuickPitch 2P Tent", 129.99, "Sports"),
    ]

    # inventory: mix of healthy, low-stock, and out-of-stock
    stock_levels = [42, 115, 28, 5, 190, 480, 2, 55, 70, 140,
                    38, 3, 85, 0, 290, 50, 170, 20, 4, 13]
    reorder_levels = [10, 20, 10, 15, 25, 50, 10, 10, 15, 20,
                      8, 10, 15, 10, 30, 10, 20, 5, 10, 5]
    reserved = [3, 8, 2, 0, 15, 20, 1, 5, 0, 10,
                2, 3, 0, 0, 25, 0, 12, 0, 2, 1]

    inventory = []
    for i, (sku, name, price, cat) in enumerate(products):
        qty = stock_levels[i]
        res = reserved[i]
        reorder = reorder_levels[i]
        avail = qty - res
        low = avail <= reorder
        inventory.append({
            "sku": sku,
            "name": name,
            "quantity": qty,
            "reserved": res,
            "available": avail,
            "reorder_level": reorder,
            "is_low_stock": low,
        })

    # recent orders with mixed statuses
    names = [
        "Alice Johnson", "Bob Smith", "Carol Williams", "Dave Brown",
        "Eve Davis", "Frank Miller", "Grace Lee", "Hank Wilson",
        "Ivy Chen", "Jack Taylor", "Kate Moore", "Leo Martinez",
        "Mia Anderson", "Noah Thomas", "Olivia Jackson",
    ]
    statuses_weighted = (["completed"] * 12) + (["pending"] * 3) + (["processing"] * 2) + (["failed"] * 2)

    random.seed(42)  # repeatable demo
    orders = []
    for i in range(20):
        status = random.choice(statuses_weighted)
        customer = random.choice(names)
        items_count = random.randint(1, 4)
        total = round(random.uniform(25, 1500), 2)
        created = now - timedelta(minutes=random.randint(5, 1440))
        orders.append({
            "order_id": f"SHP-{10001 + i}",
            "customer": customer,
            "total": total,
            "status": status,
            "items": items_count,
            "created_at": created,
        })
    orders.sort(key=lambda o: o["created_at"], reverse=True)

    # sync logs (celery task results)
    task_statuses = (["success"] * 14) + (["failure"] * 3) + (["retry"] * 3)
    logs = []
    for i in range(30):
        ts = random.choice(task_statuses)
        task = random.choice(["process_order", "process_order", "sync_inventory"])
        dur = random.randint(45, 800) if ts != "retry" else random.randint(200, 1200)
        created = now - timedelta(minutes=random.randint(2, 720))
        entry = {
            "task_name": task,
            "status": ts.upper(),
            "duration_ms": dur,
            "order_id": random.randint(1, 20) if task == "process_order" else None,
            "created_at": created,
            "error_message": None,
            "traceback": None,
            "task_id": f"celery-{random.randint(10000, 99999)}",
        }
        if ts == "failure":
            entry["error_message"] = random.choice([
                "Product with SKU 'NONEXISTENT' not found in catalog",
                "Insufficient stock for 'WATCH-001': requested=5, available=3",
                "ConnectionError: database connection pool exhausted",
            ])
            entry["traceback"] = f"Traceback (most recent call last):\n  File \"app/tasks/order_tasks.py\", line 72\n    raise ValueError(\"{entry['error_message']}\")\nValueError: {entry['error_message']}"
        logs.append(entry)
    logs.sort(key=lambda l: l["created_at"], reverse=True)

    # aggregate metrics
    completed = sum(1 for o in orders if o["status"] == "completed")
    failed = sum(1 for o in orders if o["status"] == "failed")
    pending = sum(1 for o in orders if o["status"] in ("pending", "processing"))
    total = len(orders)
    rate = round(completed / total * 100, 1) if total > 0 else 0
    low_count = sum(1 for inv in inventory if inv["is_low_stock"])
    durations = [l["duration_ms"] for l in logs if l["status"] == "SUCCESS"]
    avg_ms = f"{int(sum(durations) / len(durations))}ms" if durations else "N/A"

    return {
        "inventory": inventory,
        "orders": orders,
        "logs": logs,
        "failed_logs": [l for l in logs if l["status"] == "FAILURE"],
        "metrics": {
            "total": total, "completed": completed, "failed": failed,
            "pending": pending, "success_rate": rate,
            "low_stock": low_count, "avg_time": avg_ms,
        },
        "health": {"db": True, "redis": True},
    }


def _fetch_live_data():
    """Pull real data from PostgreSQL."""
    from sqlalchemy import func, desc, text
    from sqlalchemy.orm import joinedload
    from app.db.base import SessionLocal
    from app.db.models import Order, OrderStatus, Inventory, SyncLog, SyncStatus

    db = SessionLocal()
    try:
        total = db.query(func.count(Order.id)).scalar() or 0
        completed = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.COMPLETED).scalar() or 0
        failed = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.FAILED).scalar() or 0
        pending = db.query(func.count(Order.id)).filter(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.PROCESSING])
        ).scalar() or 0
        rate = round(completed / total * 100, 1) if total > 0 else 0

        avg_t = db.query(func.avg(SyncLog.duration_ms)).filter(
            SyncLog.status == SyncStatus.SUCCESS, SyncLog.task_name == "process_order"
        ).scalar()
        avg_str = f"{int(avg_t)}ms" if avg_t else "N/A"

        all_inv = db.query(Inventory).options(joinedload(Inventory.product)).all()
        low_count = sum(1 for inv in all_inv if inv.is_low_stock)

        inv_list = []
        for inv in all_inv:
            pname = inv.product.name if inv.product else f"Product {inv.product_id}"
            inv_list.append({
                "sku": inv.product.sku if inv.product else "?",
                "name": pname,
                "quantity": inv.quantity, "reserved": inv.reserved,
                "available": inv.available, "reorder_level": inv.reorder_level,
                "is_low_stock": inv.is_low_stock,
            })

        recent_orders = db.query(Order).options(joinedload(Order.items)).order_by(desc(Order.created_at)).limit(20).all()
        orders = []
        for o in recent_orders:
            sv = o.status.value if isinstance(o.status, OrderStatus) else o.status
            orders.append({
                "order_id": o.external_order_id,
                "customer": o.customer_name or "N/A",
                "total": o.total_amount,
                "status": sv,
                "items": len(o.items) if o.items else 0,
                "created_at": o.created_at,
            })

        all_logs = db.query(SyncLog).order_by(desc(SyncLog.created_at)).limit(50).all()
        logs = []
        for l in all_logs:
            sv = l.status.value if isinstance(l.status, SyncStatus) else l.status
            logs.append({
                "task_name": l.task_name, "status": sv.upper(),
                "duration_ms": l.duration_ms or 0, "order_id": l.order_id,
                "created_at": l.created_at, "error_message": l.error_message,
                "traceback": l.traceback, "task_id": l.task_id,
            })

        db_ok = True
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            db_ok = False

        redis_ok = True
        try:
            import redis as _r
            _r.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0")).ping()
        except Exception:
            redis_ok = False

        return {
            "inventory": inv_list, "orders": orders, "logs": logs,
            "failed_logs": [l for l in logs if l["status"] == "FAILURE"],
            "metrics": {
                "total": total, "completed": completed, "failed": failed,
                "pending": pending, "success_rate": rate,
                "low_stock": low_count, "avg_time": avg_str,
            },
            "health": {"db": db_ok, "redis": redis_ok},
        }
    except Exception as e:
        st.error(f"Database error: {e}")
        return _generate_demo_data()
    finally:
        db.close()


# -- Load data -----------------------------------------------------------------

if DEMO_MODE:
    data = _generate_demo_data()
else:
    data = _fetch_live_data()

metrics = data["metrics"]
inventory = data["inventory"]
orders = data["orders"]
logs = data["logs"]
failed_logs = data["failed_logs"]
health = data["health"]


# -- Sidebar -------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 📦 Fulfil ERP")
    st.markdown("**Monitoring Dashboard**")
    st.markdown("---")

    if DEMO_MODE:
        st.info("Running in **demo mode** with sample data")

    auto_refresh = st.toggle("🔄 Auto-refresh", value=not DEMO_MODE)
    refresh_interval = st.slider("Refresh interval (sec)", 5, 60, 10) if auto_refresh else 10

    st.markdown("---")
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.markdown(
        f"<small style='color:#8892b0;'>Last updated: {datetime.now().strftime('%H:%M:%S')}</small>",
        unsafe_allow_html=True,
    )


# -- Helpers -------------------------------------------------------------------

def status_badge(status):
    cls = {
        "completed": "badge-completed", "pending": "badge-pending",
        "processing": "badge-processing", "failed": "badge-failed",
    }.get(status.lower(), "badge-pending")
    return f'<span class="status-badge {cls}">{status}</span>'


def kpi_card(value, label, css="kpi-blue"):
    return f"""
    <div class="kpi-card">
        <p class="kpi-value {css}">{value}</p>
        <p class="kpi-label">{label}</p>
    </div>
    """


# -- Header --------------------------------------------------------------------

st.markdown("# 📦 Fulfil ERP — Monitoring Dashboard")
st.markdown(
    "<p style='color: #8892b0; margin-top: -10px;'>Real-time order processing & inventory monitoring</p>",
    unsafe_allow_html=True,
)


# -- KPI cards -----------------------------------------------------------------

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(kpi_card(metrics["total"], "Total Orders", "kpi-blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card(f"{metrics['success_rate']}%", "Success Rate", "kpi-green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card(metrics["failed"], "Failed", "kpi-red"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card(metrics["avg_time"], "Avg Process Time", "kpi-purple"), unsafe_allow_html=True)
with c5:
    ac = "kpi-red" if metrics["low_stock"] > 0 else "kpi-green"
    st.markdown(kpi_card(metrics["low_stock"], "Low Stock Alerts", ac), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# -- Orders + Inventory --------------------------------------------------------

left, right = st.columns([3, 2])

with left:
    st.markdown('<div class="section-header">📋 Live Order Feed</div>', unsafe_allow_html=True)
    if orders:
        for o in orders:
            badge = status_badge(o["status"])
            row = st.columns([2, 2, 1.5, 1.5])
            with row[0]:
                st.markdown(f"**#{o['order_id']}**")
            with row[1]:
                st.markdown(o["customer"])
            with row[2]:
                st.markdown(f"${o['total']:.2f}")
            with row[3]:
                st.markdown(badge, unsafe_allow_html=True)
    else:
        st.info("No orders yet — send a webhook to get started.")

with right:
    st.markdown('<div class="section-header">📊 Inventory Levels</div>', unsafe_allow_html=True)
    if inventory:
        inv_df = pd.DataFrame(inventory)
        inv_df["short_name"] = inv_df["name"].str[:20]
        colors = ["#ff5370" if ls else "#64ffda" for ls in inv_df["is_low_stock"]]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=inv_df["short_name"], y=inv_df["available"],
            marker_color=colors, name="Available",
            text=inv_df["available"], textposition="auto",
        ))
        fig.add_trace(go.Scatter(
            x=inv_df["short_name"], y=inv_df["reorder_level"],
            mode="lines+markers", name="Reorder Level",
            line=dict(color="#ffcb6b", dash="dash", width=2),
            marker=dict(size=6),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ccd6f6"), height=350,
            margin=dict(l=20, r=20, t=20, b=60),
            legend=dict(orientation="h", y=-0.2),
            xaxis=dict(tickangle=-45, gridcolor="#1a1f2e"),
            yaxis=dict(gridcolor="#1a1f2e"),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No inventory data available.")


# -- Celery task monitor -------------------------------------------------------

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">⚙️ Celery Task Monitor</div>', unsafe_allow_html=True)

if logs:
    log_df = pd.DataFrame(logs)
    tc1, tc2 = st.columns(2)

    with tc1:
        counts = log_df["status"].value_counts()
        cmap = {"SUCCESS": "#64ffda", "FAILURE": "#ff5370", "RETRY": "#ffcb6b"}
        pie_colors = [cmap.get(s, "#82aaff") for s in counts.index]

        fig_pie = go.Figure(data=[go.Pie(
            labels=counts.index, values=counts.values,
            marker_colors=pie_colors, hole=0.5,
            textinfo="label+value", textfont=dict(size=12),
        )])
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ccd6f6"), height=280,
            margin=dict(l=20, r=20, t=30, b=20),
            title=dict(text="Task Status Distribution", font=dict(size=14)),
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with tc2:
        timed = log_df[log_df["duration_ms"] > 0].head(15)
        if not timed.empty:
            fig_bar = go.Figure(data=[go.Bar(
                x=list(range(len(timed))), y=timed["duration_ms"],
                marker_color=["#64ffda" if s == "SUCCESS" else "#ff5370" for s in timed["status"]],
                text=timed["task_name"], textposition="auto",
            )])
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ccd6f6"), height=280,
                margin=dict(l=20, r=20, t=30, b=20),
                title=dict(text="Task Duration (ms)", font=dict(size=14)),
                xaxis=dict(title="Task #", gridcolor="#1a1f2e"),
                yaxis=dict(title="Duration (ms)", gridcolor="#1a1f2e"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No timing data yet.")
else:
    st.info("No task logs yet — process an order to see activity.")


# -- Failed sync logs ----------------------------------------------------------

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">🚨 Failed Sync Logs</div>', unsafe_allow_html=True)

if failed_logs:
    for fl in failed_logs:
        ts = fl["created_at"].strftime("%Y-%m-%d %H:%M:%S") if fl["created_at"] else "Unknown"
        with st.expander(f"❌ {fl['task_name']} — {ts}", expanded=False):
            a, b = st.columns(2)
            with a:
                st.markdown(f"**Task ID:** `{fl.get('task_id', 'N/A')}`")
                st.markdown(f"**Order ID:** {fl.get('order_id', 'N/A')}")
            with b:
                st.markdown(f"**Duration:** {fl.get('duration_ms', 0)}ms")
            if fl.get("error_message"):
                st.error(f"**Error:** {fl['error_message']}")
            if fl.get("traceback"):
                st.code(fl["traceback"], language="python")
else:
    st.success("✅ No failed tasks — all syncs are healthy.")


# -- System health -------------------------------------------------------------

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">💚 System Health</div>', unsafe_allow_html=True)

h1, h2, h3 = st.columns(3)
with h1:
    dot = "health-green" if health["db"] else "health-red"
    txt = "Connected" if health["db"] else "Disconnected"
    st.markdown(f'<span class="health-dot {dot}"></span> **PostgreSQL** — {txt}', unsafe_allow_html=True)
with h2:
    dot = "health-green" if health["redis"] else "health-red"
    txt = "Connected" if health["redis"] else "Disconnected"
    st.markdown(f'<span class="health-dot {dot}"></span> **Redis** — {txt}', unsafe_allow_html=True)
with h3:
    ok = health["db"] and health["redis"]
    dot = "health-green" if ok else "health-red"
    txt = "All Systems Operational" if ok else "Degraded"
    st.markdown(f'<span class="health-dot {dot}"></span> **Overall** — {txt}', unsafe_allow_html=True)


# -- Auto-refresh --------------------------------------------------------------

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
