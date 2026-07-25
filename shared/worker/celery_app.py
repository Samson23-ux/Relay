import sentry_sdk
from celery import Celery

from shared import get_global_settings

SETTINGS = get_global_settings()

sentry_sdk.init(
    dsn=SETTINGS.SENTRY_SDK_DSN,
    enable_logs=True,
    send_default_pii=True,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    profile_lifecycle="trace",
)

celery_app = Celery(
    main="celery_app",
    broker=SETTINGS.BROKER_URL,
    backend=SETTINGS.REDIS_URL,
)

celery_app.config_from_object("shared.worker.celeryconfig")
celery_app.autodiscover_tasks("shared.worker.tasks.log")
