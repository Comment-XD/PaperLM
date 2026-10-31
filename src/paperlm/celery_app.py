from celery import Celery
from paperlm.config import get_settings

settings = get_settings()
app = Celery("paperlm", broker=settings.redis_url, include=["paperlm.tasks"])

app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": settings.visibility_timeout_seconds},
)