import time
from uuid import UUID
from celery.exceptions import TimeoutError as CeleryTimeoutError


from shared.core.exceptions import ServiceUnavailable
from apps.order_service.app.api.schemas.cart import CartInDB
from shared.utils import get_message_meta, update_db_log, log_error
from apps.product_service.app.worker.tasks.product import get_product
from apps.order_service.app.api.schemas.order_item import OrderItemResponse
from apps.product_service.app.api.schemas.product import ProductInDB, ProductItem
from apps.order_service.app.api.schemas.cart_item import CartItemResponse, CartItemInDB
from apps.product_service.app.worker.tasks.product import process_reservation, restore_product_quantity

# how long to wait for a product_service task result before giving up rather
# than blocking the request (and its event loop) indefinitely
TASK_RESULT_TIMEOUT = 10


async def fetch_product(product_id: UUID, request_meta: dict) -> ProductInDB:
    message_meta: dict = get_message_meta(request_meta, "product_service")

    start_time = time.perf_counter()
    res = get_product.apply_async(
        priority=5,
        kwargs={"product_id": str(product_id), "request_meta": message_meta},
    )

    try:
        result = res.get(timeout=TASK_RESULT_TIMEOUT)
    except CeleryTimeoutError as exc:
        message = f"Timed out waiting for product {product_id} to be fetched"
        log_error(message, request_meta)
        raise ServiceUnavailable() from exc

    elapsed = (time.perf_counter() - start_time) * 1000
    latency = f"{elapsed:.2f}ms"

    span_id = result.get("span_id")
    update_db_log(message_meta.get("trace_id"), span_id, {"latency_ms": latency})

    return ProductInDB.model_validate(result.get("data"))


async def reserve_product(payload: dict, request_meta: dict):
    message_meta: dict = get_message_meta(request_meta, "product_service")

    start_time = time.perf_counter()
    res = process_reservation.apply_async(
        priority=5, kwargs={"payload": payload, "request_meta": message_meta}
    )

    try:
        result = res.get(timeout=TASK_RESULT_TIMEOUT)
    except CeleryTimeoutError as exc:
        message = (
            f"Timed out waiting for reservation event '{payload.get('event')}' "
            f"on order {payload.get('order_id')}"
        )
        log_error(message, request_meta)
        raise ServiceUnavailable() from exc

    elapsed = (time.perf_counter() - start_time) * 1000
    latency = f"{elapsed:.2f}ms"

    span_id = result.get("span_id")
    update_db_log(
        request_meta.get("trace_id"), span_id, {"latency_ms": latency}
    )


async def restore_product(payload: dict, request_meta: dict):
    message_meta: dict = get_message_meta(request_meta, "product_service")

    start_time = time.perf_counter()
    res = restore_product_quantity.apply_async(
        priority=5, kwargs={"payload": payload, "request_meta": message_meta}
    )

    try:
        result = res.get(timeout=TASK_RESULT_TIMEOUT)
    except CeleryTimeoutError as exc:
        message = (
            f"Timed out waiting for quantity restore of products "
            f"{list(payload.get('products', {}).keys())}"
        )
        log_error(message, request_meta)
        raise ServiceUnavailable() from exc

    elapsed = (time.perf_counter() - start_time) * 1000
    latency = f"{elapsed:.2f}ms"

    span_id = result.get("span_id")
    update_db_log(
        request_meta.get("trace_id"), span_id, {"latency_ms": latency}
    )


def serialize_cart_item(item: CartItemInDB) -> dict:
    data: dict = item.model_dump()
    data["product_id"] = str(data["product_id"])
    data["price"] = str(data["price"])
    data["total_price"] = str(data["total_price"])
    data["created_at"] = data["created_at"].isoformat()
    return data


def serialize_cart(cart: CartInDB) -> dict:
    data: dict = cart.model_dump(exclude={"cart_items"})
    data["id"] = str(data["id"])
    data["user_id"] = str(data["user_id"])
    data["created_at"] = data["created_at"].isoformat()
    data["cart_items"] = [serialize_cart_item(item) for item in cart.cart_items]
    return data


def get_items_response(obj: str, obj_items: list[tuple]):
    items = []
    for obj_item in obj_items:
        product = ProductItem(
            product_id=obj_item[0],
            name=obj_item[1],
            description=obj_item[2],
            serial=obj_item[3],
        )

        if obj == "cart":
            item = CartItemResponse(
                product=product,
                quantity=obj_item[4],
                price=obj_item[5],
                total_price=obj_item[6],
                created_at=obj_item[7],
                cart_id=obj_item[8],
            )
        elif obj == "order":
            item = OrderItemResponse(
                order_id=obj_item[8],
                product=product,
                quantity=obj_item[4],
                price=obj_item[5],
                total_price=obj_item[6],
                created_at=obj_item[7],
            )

        items.append(item)
    return items
