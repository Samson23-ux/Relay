import time
from decimal import Decimal
from sqlalchemy import Sequence
from uuid import UUID, uuid4, uuid7


from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from shared.repo.uow import UnitOfWorkRepository
from apps.user_service.app.api.models.user import User
from apps.order_service.app.api.models.order import Order
from apps.order_service.app.utils import get_items_response
from apps.order_service.app.api.repo.cart import CartRepository
from apps.order_service.app.api.services.cart import CartService
from apps.order_service.app.api.repo.order import OrderRepository
from apps.order_service.app.core.exceptions import CartNotFoundError
from apps.order_service.app.api.repo.cart_item import CartItemRepository
from apps.order_service.app.api.services.cart_item import CartItemService
from apps.order_service.app.api.repo.order_item import OrderItemRepository
from apps.order_service.app.api.services.order_item import OrderItemService
from apps.order_service.app.api.schemas.order import OrderResponse, OrderInDB
from shared.utils import log_error, log_info, update_db_log, get_message_meta
from apps.product_service.app.worker.tasks.product import process_reservation
from apps.order_service.app.api.schemas.order_item import (
    OrderItemResponse,
    OrderItemInDB,
)
from apps.order_service.app.core.exceptions import (
    OrderNotFoundError,
    OrdersNotFoundError,
)


class OrderService:
    def __init__(self, order_repo: OrderRepository, redis_repo: RedisRepository):
        self._uow = None
        self._cart_service = None
        self._order_repo = order_repo
        self._redis_repo = redis_repo
        self._cart_item_service = None
        self._order_item_service = None

    async def _set_transc(self, uow: UnitOfWorkRepository):
        await self._order_repo.aclose()

        self._uow = uow
        self._order_repo._async_session = self._uow.session

        self._cart_service = CartService(
            cart_repo=CartRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )
        self._cart_item_service = CartItemService(
            item_repo=CartItemRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )
        self._order_item_service = OrderItemService(
            item_repo=OrderItemRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )

    async def get_orders(
        self,
        items: bool,
        curr_user: User,
        order: str,
        sort: str | None,
        request_meta: dict,
        order_item_service: OrderItemService,
    ) -> list[OrderResponse | OrderItemResponse]:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            if items:
                items_db: Sequence[Order] = (
                    await order_item_service._get_orders_with_items(
                        user_id, sort, order
                    )
                )

                if not items_db:
                    message = "User orders not found in database"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise OrdersNotFoundError()

                orders = get_items_response("order", items_db)

                message = "User orders retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                return orders
            else:
                orders_db: Sequence[Order] = await self._order_repo._get_records(
                    order, sort, user_id=user_id
                )

                if not orders_db:
                    message = "User orders not found in database"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise OrdersNotFoundError()

                orders: list[OrderResponse] = [
                    OrderResponse.model_validate(o) for o in orders_db
                ]

                message = "User orders retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                return orders
        except Exception as exc:
            if isinstance(exc, OrdersNotFoundError):
                raise OrdersNotFoundError()

            message = f"Error occured while retrieving orders. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def get_order_id(
        self,
        id: UUID,
        items: bool,
        curr_user: User,
        request_meta: dict,
        order_item_service: OrderItemService,
    ) -> OrderResponse | list[OrderItemResponse]:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            if items:
                items_db = await order_item_service._get_order_with_items(
                    user_id, order_id=id
                )

                if not items_db:
                    message = f"User order not found with id {id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise OrderNotFoundError(id=id)

                order = get_items_response("order", items_db)

                message = "User order retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_info(message, request_meta, circuit)
                return order
            else:
                order_db: Order | None = await self._order_repo.get_record(
                    id=id, user_id=user_id
                )

                if not order_db:
                    message = f"User order not found with id {id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise OrderNotFoundError(id=id)

                message = "User order retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_info(message, request_meta, circuit)
                return OrderResponse.model_validate(order_db)
        except Exception as exc:
            if isinstance(exc, OrderNotFoundError):
                raise OrderNotFoundError(id=id)

            message = (
                f"Error occured while retrieving order with id {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def create_order(
        self,
        cart_id: UUID,
        curr_user: User,
        request_meta: dict,
        uow: UnitOfWorkRepository,
    ) -> OrderResponse:
        await self._set_transc(uow)

        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            order_id = uuid7()
            products_details = {}

            # get cart for ownership confirmation and cart items
            await self._cart_service._get_cart(
                False, request_meta, id=cart_id, user_id=user_id
            )
            cart_items = await self._cart_item_service._get_cart_items(cart_id=cart_id)

            products = {prd_id: quan for prd_id, quan in cart_items}
            message_meta: dict = get_message_meta(request_meta, "product_service")
            payload: dict = {
                "event": "reserve",
                "order_id": str(order_id),
                "message_id": str(uuid4()),
                "products": products,
            }

            # reserve products
            start_time = time.perf_counter()
            res = process_reservation.apply_async(
                priority=5, kwargs={"payload": payload, "request_meta": message_meta}
            )
            total = (time.perf_counter() - start_time) * 1000

            span_id = res.get("span_id")
            update_db_log(
                span_id, request_meta.get("trace_id"), {"latency_ms": int(total)}
            )

            products_details: dict = res.get("data")

            total_price = 0
            order_items: list[dict] = []

            # prepare list of order items
            for prod_id, details in products_details.items():
                price, quantity = details

                order_item: OrderItemInDB = OrderItemInDB(
                    order_id=order_id,
                    product_id=prod_id,
                    quantity=quantity,
                    price=price,
                    total_price=Decimal(price) * quantity,
                ).model_dump()

                total_price += order_item["total_price"]
                order_items.append(order_item)

            order: OrderInDB = OrderInDB(
                id=order_id,
                user_id=user_id,
                reference_id=uuid4(),
                total_price=total_price,
            )

            # create order and order items
            self._order_repo.add(entity=order)
            await self._order_repo.flush()

            await self._order_item_service.create_order_items(order_items)

            await self._uow.commit()

            # confirm product reservation
            payload["event"] = "confirm"
            payload["message_id"] = str(uuid4())
            payload["products"] = [prd_id for prd_id, _ in products_details.items()]

            start_time = time.perf_counter()
            res = process_reservation.apply_async(
                priority=5, kwargs={"payload": payload, "request_meta": message_meta}
            )
            total = (time.perf_counter() - start_time) * 1000

            span_id = res.get("span_id")
            update_db_log(
                span_id, request_meta.get("trace_id"), {"latency_ms": int(total)}
            )

            # return order
            order_db: Order = await self._order_repo.get_record(
                id=order_id, user_id=user_id
            )

            message = "Order created successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return OrderResponse.model_validate(order_db)
        except Exception as exc:
            await self._uow.rollback()

            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)

            # release_reserve
            payload["event"] = "release_reserve"
            payload["message_id"] = str(uuid4())
            payload["products"] = [prd_id for prd_id, _ in products_details.items()]

            start_time = time.perf_counter()
            res = process_reservation.apply_async(
                priority=5, kwargs={"payload": payload, "request_meta": message_meta}
            )
            total = (time.perf_counter() - start_time) * 1000

            span_id = res.get("span_id")
            update_db_log(
                span_id, request_meta.get("trace_id"), {"latency_ms": int(total)}
            )

            message = f"Error occured while creating order with cart_id {cart_id}. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def delete_order(self, id: UUID, curr_user: User, request_meta: dict):
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            order: Order | None = await self._order_repo.get_record(
                id=id, user_id=user_id
            )

            if not order:
                message = f"User order not found with id {id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise OrderNotFoundError(id=id)

            await self._order_repo.delete(model=order)
            await self._order_repo.commit()

            message = "User order deleted successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)
            log_info(message, request_meta, circuit)
        except Exception as exc:
            await self._order_repo.rollback()

            if isinstance(exc, OrderNotFoundError):
                raise OrderNotFoundError(id=id)

            message = (
                f"Error occured while deleting order with id {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc
