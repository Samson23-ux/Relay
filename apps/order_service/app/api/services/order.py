from decimal import Decimal
from sqlalchemy import Sequence
from uuid import UUID, uuid4, uuid7


from shared.utils import log_error, log_info
from shared.repo.redis import RedisRepository
from shared.repo.uow import UnitOfWorkRepository
from apps.user_service.app.api.models.user import User
from apps.order_service.app.utils import get_items_response
from apps.order_service.app.api.repo.cart import CartRepository
from apps.order_service.app.api.services.cart import CartService
from apps.order_service.app.api.repo.order import OrderRepository
from shared.core.exceptions import ServerError, ServiceUnavailable
from apps.order_service.app.core.exceptions import CartNotFoundError
from apps.order_service.app.api.models.order import Order, OrderStatus
from apps.order_service.app.utils import reserve_product, restore_product
from apps.order_service.app.api.services.cart_item import CartItemService
from apps.order_service.app.api.repo.order_item import OrderItemRepository
from apps.order_service.app.api.services.order_item import OrderItemService
from apps.order_service.app.api.schemas.order import OrderResponse, OrderInDB

# from apps.product_service.app.worker.tasks.product import process_reservation
from apps.order_service.app.api.schemas.order_item import (
    OrderItemResponse,
    OrderItemInDB,
)
from apps.product_service.app.core.exceptions import (
    OutOfStockError,
    NotEnoughStockError,
    TaskOutOfStockError,
    ProductNotFoundError,
    TaskNotEnoughStockError,
    TaskProductNotFoundError,
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

        cart_repo = CartRepository(redis_repo=self._redis_repo)

        self._cart_service = CartService(
            cart_repo=cart_repo,
            redis_repo=self._redis_repo,
        )
        self._cart_item_service = CartItemService(
            cart_repo=cart_repo,
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

        payload = None
        products = {}

        try:
            order_id = uuid7()

            total_price = 0
            order_items: list[dict] = []

            # get cart for ownership confirmation
            cart: dict = await self._cart_service._get_cart(
                request_meta, id=cart_id, user_id=user_id
            )

            cart_items: list[dict] = cart.get("cart_items")
            products = {
                item["product_id"]: (item["price"], item["quantity"])
                for item in cart_items
            }

            # prepare list of order items
            for prod_id, details in products.items():
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

            # create order and items, and commit as processing: the reservation
            # task runs on a separate worker connection, which under READ
            # COMMITTED can't see these rows until they're committed. Committing
            # the items here too means a cancelled order still shows what was ordered.
            await self._order_repo.insert_order(order)
            await self._order_item_service.create_order_items(order_items)
            await self._uow.commit()

            payload: dict = {
                "event": "reserve",
                "order_id": str(order_id),
                "message_id": str(uuid4()),
                "products": {
                    prd_id: quantity for prd_id, (_, quantity) in products.items()
                },
            }

            # reserve products
            await reserve_product(payload, request_meta)

            # confirm product reservation
            payload["event"] = "confirm"
            payload["message_id"] = str(uuid4())
            payload["products"] = [prd_id for prd_id, _ in products.items()]

            await reserve_product(payload, request_meta)

            # quantities are now deducted; mark the order confirmed so a
            # later deletion knows to restore stock rather than release a hold
            await self._order_repo.update_records(
                {"status": OrderStatus.CONFIRMED}, id=order_id
            )
            await self._uow.commit()

            # delete cart
            await self._cart_service._delete_cart(cart_id, user_id)

            # return order
            order_db: Order = await self._order_repo.get_record(
                id=order_id, user_id=user_id
            )

            message = "Order created successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return OrderResponse.model_validate(order_db)
        except (
            TaskOutOfStockError,
            TaskNotEnoughStockError,
            TaskProductNotFoundError,
        ) as exc:
            prd_id = exc.id

            # order was already committed as processing; the reservation failed,
            # so the order is invalid and must be cancelled explicitly
            await self._order_repo.update_records(
                {"status": OrderStatus.CANCELLED}, id=order_id
            )
            await self._uow.commit()

            if isinstance(exc, TaskProductNotFoundError):
                message = f"Product not found with id: {prd_id}"
                log_error(message, request_meta)

                raise ProductNotFoundError(id=prd_id)
            elif isinstance(exc, TaskOutOfStockError):
                message = f"Product out of stock. Id: {prd_id}"
                log_error(message, request_meta)

                raise OutOfStockError(id=prd_id)
            elif isinstance(exc, TaskNotEnoughStockError):
                message = f"Product stock not enough. Id: {prd_id}"
                log_error(message, request_meta)

                raise NotEnoughStockError(id=prd_id)
        except Exception as exc:
            await self._uow.rollback()

            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)

            message = (
                f"Error occured while creating order with cart_id {cart_id}."
                f"Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            if payload:
                # order was already committed as processing by this point; release
                # any reservation and cancel the order regardless of that outcome
                payload["event"] = "release_reserve"
                payload["message_id"] = str(uuid4())
                payload["products"] = [prd_id for prd_id, _ in products.items()]

                try:
                    await reserve_product(payload, request_meta)
                except Exception as release_exc:
                    log_error(
                        f"Error occured while releasing reservation for order "
                        f"{order_id}. Error: {str(release_exc)}",
                        request_meta,
                        circuit,
                    )

                await self._order_repo.update_records(
                    {"status": OrderStatus.CANCELLED}, id=order_id
                )
                await self._uow.commit()

            log_error(message, request_meta, circuit)

            if isinstance(exc, ServiceUnavailable):
                raise ServiceUnavailable() from exc
            raise ServerError() from exc

    async def delete_order(
        self,
        id: UUID,
        curr_user: User,
        request_meta: dict,
        order_item_service: OrderItemService,
    ):
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            order = await order_item_service._get_orders_for_deletion(
                user_id,
                order_id=id,
            )

            if not order:
                message = f"User order not found with id {id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise OrderNotFoundError(id=id)

            order_status, _, _ = order[0]

            products = {}
            for item in order:
                _, prd_id, quantity = item
                products[str(prd_id)] = quantity

            if order_status == OrderStatus.CONFIRMED:
                # quantities were already deducted on confirm; credit them back
                payload = {"message_id": str(uuid4()), "products": products}
                await restore_product(payload, request_meta)
            elif order_status == OrderStatus.PROCESSING:
                # only reserved so far, never deducted; release the hold instead
                payload = {
                    "event": "release_reserve",
                    "order_id": str(id),
                    "message_id": str(uuid4()),
                    "products": list(products.keys()),
                }
                await reserve_product(payload, request_meta)
            # cancelled orders were already compensated for at cancellation
            # time, and delivered orders have no reservation left to undo

            await self._order_repo.delete_order(id)
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

            if isinstance(exc, ServiceUnavailable):
                raise ServiceUnavailable() from exc
            raise ServerError() from exc
