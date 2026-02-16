"""
Celery app — broker config, task routing, and beat schedule.
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery = Celery(
    "fulfil_erp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    # serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    result_expires=3600,

    # routing
    task_routes={
        "app.tasks.order_tasks.*": {"queue": "orders"},
        "app.tasks.inventory_tasks.*": {"queue": "default"},
    },

    # retries
    task_default_retry_delay=60,
    task_max_retries=3,

    # periodic tasks
    beat_schedule={
        "sync-inventory-every-5-minutes": {
            "task": "app.tasks.inventory_tasks.sync_inventory",
            "schedule": settings.INVENTORY_SYNC_INTERVAL_SECONDS,
            "options": {"queue": "default"},
        },
    },
)

celery.autodiscover_tasks(["app.tasks"])
