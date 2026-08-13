import psycopg2
from uuid import UUID
from celery.exceptions import Reject


from shared.models.log import Log
from shared.worker.celery_app import celery_app
from shared.core.exceptions import MaxRetriesError
from shared.schemas.log import LogCreate, LogUpdate
from shared.worker.tasks.base import BaseTaskWithFailure
from shared.core.shared_config import get_global_settings
from shared.worker.services import get_log_service, get_redis_repo

SETTINGS = get_global_settings()


@celery_app.task(bind=True, base=BaseTaskWithFailure)
def save_log(self, payload: dict):
    redis_repo = get_redis_repo()
    log_service = get_log_service()

    try:
        span_id: str = UUID(payload.get("span_id"))
        trace_id: str = UUID(payload.get("trace_id"))

        key: str = f"log:{trace_id}:{span_id}"
        log_exists: str | None = redis_repo.sync_get_key(key)

        if not log_exists:
            log_create: LogCreate = LogCreate.model_validate(payload)
            log_service.create_log(log_create)

            redis_repo.mark_task_processed(key, "1", SETTINGS.IDEMPOTENCY_KEY_TTL)
    except (
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
        psycopg2.extensions.TransactionRollbackError,
    ) as exc:
        try:
            raise self.retry(
                exc=MaxRetriesError(str(exc)), countdown=self._backoff_countdown()
            )
        except MaxRetriesError as exc:
            raise Reject(exc, requeue=False)
    except Exception as exc:
        raise Reject(exc, requeue=False)


@celery_app.task(bind=True, base=BaseTaskWithFailure)
def update_log(self, trace_id: str, span_id: str, payload: dict):
    redis_repo = get_redis_repo()
    log_service = get_log_service()

    try:
        trace_id: str = UUID(trace_id)
        span_id: str = UUID(span_id)

        key: str = f"log:{trace_id}:{span_id}"
        log_exists: str | None = redis_repo.sync_get_key(key)

        if not log_exists:
            log_db: Log | None = log_service.get_log(trace_id, span_id)

            if log_db:
                log_update: dict = LogUpdate.model_validate(payload).model_dump()

                for k, v in log_update.items():
                    setattr(log_db, k, v)
                log_service.update_log(log_db)
            redis_repo.mark_task_processed(key, "1", SETTINGS.IDEMPOTENCY_KEY_TTL)
    except (
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
        psycopg2.extensions.TransactionRollbackError,
    ) as exc:
        try:
            raise self.retry(
                exc=MaxRetriesError(str(exc)), countdown=self._backoff_countdown()
            )
        except MaxRetriesError as exc:
            raise Reject(exc, requeue=False)
    except Exception as exc:
        raise Reject(exc, requeue=False)
