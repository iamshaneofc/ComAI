from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "automation_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Workers acknowledge after task returns so crashes mid-task redeliver (pair with idempotent handlers).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    # Default retry spacing when code calls ``retry()`` without ``countdown`` (we set countdown explicitly).
    task_default_retry_delay=30,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_routes={
        "app.tasks.automation_tasks.*": {"queue": "default"},
        "app.tasks.message_tasks.*": {"queue": "default"},
    },
)

# Register task modules (worker entrypoint: celery -A app.core.celery_app worker)
import app.tasks.automation_tasks  # noqa: E402, F401
import app.tasks.message_tasks  # noqa: E402, F401
