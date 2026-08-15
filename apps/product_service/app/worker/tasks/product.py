import psycopg2
from uuid import uuid4, UUID
from celery.exceptions import Reject


from shared.worker.celery_app import celery_app
from shared.worker.services import get_redis_repo
from shared.core.exceptions import MaxRetriesError
from shared.worker.tasks.base import BaseTaskWithFailure
from shared.core.shared_config import get_global_settings
from apps.product_service.app.api.schemas.product import ProductInDB
from apps.product_service.app.core.exceptions import ProductNotFoundError
from apps.product_service.app.worker.services import get_product_service, get_uow

GLOBAL_SETTINGS = get_global_settings()


@celery_app.task(bind=True, base=BaseTaskWithFailure)
def get_product(self, product_id: str, request_meta: dict):
    product_service = get_product_service()

    try:
        request_meta["task_id"] = UUID(self.request.id)
        request_meta["parent_span_id"] = request_meta.get("span_id")
        request_meta["span_id"] = str(uuid4())

        product_db = product_service._get_sync_product(product_id, request_meta)
        product = ProductInDB.model_validate(product_db)

        product.id = str(product.id)
        product.price = str(product.price)
        product.created_at = product.created_at.isoformat()
        product.updated_at = (
            product.updated_at.isoformat() if product.updated_at else None
        )

        return {"data": product.model_dump(), "span_id": request_meta.get("span_id")}
    except ProductNotFoundError as exc:
        raise exc
    except Exception as exc:
        raise Reject(exc, requeue=False)


@celery_app.task(bind=True, base=BaseTaskWithFailure)
def process_reservation(self, payload: dict, request_meta: dict):
    uow = get_uow()
    redis = get_redis_repo()
    product_service = get_product_service()

    event: str = payload.get("event")
    message_id: str = payload.get("message_id")

    try:
        reserve_processed: str = redis.sync_get_key(f"reserve:{message_id}")

        if not reserve_processed:
            order_id: str = payload.get("order_id")
            products: dict = payload.get("products")

            request_meta["task_id"] = UUID(self.request.id)
            request_meta["parent_span_id"] = request_meta.get("span_id")
            request_meta["span_id"] = str(uuid4())

            if event == "reserve":
                res = product_service.reserve_product(
                    order_id, products, request_meta, uow
                )
            elif event == "release_reserve":
                res = product_service.release_reserve(order_id, products, request_meta)
            elif event == "confirm":
                res = product_service.confirm_reserve(order_id, products, request_meta, uow)

            redis.mark_task_processed(
                f"reserve:{message_id}", "1", GLOBAL_SETTINGS.IDEMPOTENCY_KEY_TTL
            )

        return {"data": res, "span_id": request_meta.get("span_id")}
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
