import time
from uuid import UUID, uuid7
from sqlalchemy import Sequence
from celery.exceptions import TimeoutError


from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from shared.repo.uow import UnitOfWorkRepository
from apps.user_service.app.api.models.user import User
from apps.order_service.app.api.models.cart import Cart
from apps.order_service.app.utils import get_items_response
from apps.order_service.app.api.repo.cart import CartRepository
from apps.order_service.app.api.models.cart_item import CartItem
from apps.product_service.app.worker.tasks.product import get_product
from apps.order_service.app.api.repo.cart_item import CartItemRepository
from apps.order_service.app.api.services.cart_item import CartItemService
from shared.utils import log_info, log_error, get_message_meta, update_db_log
from apps.product_service.app.api.schemas.product import ProductInDB, ProductItem
from apps.order_service.app.api.schemas.cart import CartResponse, AddToCart, CartInDB
from apps.order_service.app.api.schemas.cart_item import CartItemResponse, CartItemInDB
from apps.product_service.app.core.exceptions import (
    ProductNotFoundError,
    NotEnoughStockError,
)
from apps.order_service.app.core.exceptions import (
    CartNotFoundError,
    CartsNotFoundError,
    CartItemNotFoundError,
)


class CartService:
    def __init__(self, cart_repo: CartRepository, redis_repo: RedisRepository):
        self._uow = None
        self._item_service = None
        self._cart_repo = cart_repo
        self._redis_repo = redis_repo

    def _get_item_response(self, items: list[tuple]):
        (item,) = items
        product = ProductItem(
            id=item[0], name=item[1], description=item[2], serial=item[3]
        )
        cart_item = CartItemResponse(
            product=product,
            quantity=item[4],
            price=item[5],
            total_price=item[6],
            created_at=item[7],
        )

        return cart_item

    async def _get_cart(self, read: bool, request_meta: dict, **filters):
        try:
            cart_id: UUID = filters.get("id")
            circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

            cart: Cart | None = await self._cart_repo.get_cart_with_lock(
                read, **filters
            )

            if not cart:
                message = f"Cart not found with id {cart_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartNotFoundError(id=cart_id)
        except Exception as exc:
            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)

            message = f"Error occured while retrieving cart with id {cart_id}. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def get_carts(
        self,
        items: bool,
        curr_user: User,
        order: str,
        sort: str | None,
        request_meta: dict,
        cart_item_service: CartItemService,
    ) -> list[CartResponse | CartItemResponse]:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            if items:
                carts_db = await cart_item_service._get_carts_with_items(
                    user_id, sort, order
                )

                if not carts_db:
                    message = "User carts not found in database"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartsNotFoundError()

                carts = get_items_response("cart", carts_db)

                message = "User carts retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                return carts
            else:
                carts_db: Sequence[Cart] = await self._cart_repo._get_records(
                    order, sort, user_id=user_id
                )

                if not carts_db:
                    message = "User carts not found in database"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartsNotFoundError()

                carts: list[CartResponse] = [
                    CartResponse.model_validate(c) for c in carts_db
                ]

                message = "User carts retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                return carts
        except Exception as exc:
            if isinstance(exc, CartsNotFoundError):
                raise CartsNotFoundError()

            message = f"Error occured while retrieving carts. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def get_cart_by_id(
        self,
        id: UUID,
        items: bool,
        curr_user: User,
        request_meta: dict,
        cart_item_service: CartItemService,
    ) -> CartResponse | list[CartItemResponse]:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            if items:
                cart_db = await cart_item_service._get_cart_with_items(user_id, cart_id=id)

                if not cart_db:
                    message = f"User cart not found with id {id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartNotFoundError(id=id)

                carts = get_items_response("cart", cart_db)

                message = "User cart retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_info(message, request_meta, circuit)
                return carts
            else:
                cart_db: Cart | None = await self._cart_repo.get_record(
                    id=id, user_id=user_id
                )

                if not cart_db:
                    message = f"User cart not found with id {id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartNotFoundError(id=id)

                message = "User cart retrieved successfully"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_info(message, request_meta, circuit)
                return CartResponse.model_validate(cart_db)
        except Exception as exc:
            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=id)

            message = (
                f"Error occured while retrieving cart with id {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def create_cart(
        self,
        curr_user: User,
        request_meta: dict,
        cart_item: AddToCart,
        cart_id: UUID | None,
        uow: UnitOfWorkRepository,
    ) -> CartResponse:
        await self._cart_repo.aclose()

        self._uow = uow
        self._cart_repo._async_session = self._uow.session
        self._item_service = CartItemService(
            item_repo=CartItemRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )

        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        product_id: UUID = cart_item.product_id
        message_meta: dict = get_message_meta(request_meta, "product_service")

        try:
            start_time = time.perf_counter()
            res = get_product.apply_async(
                priority=5,
                kwargs={
                    "product_id": str(product_id),
                    "request_meta": message_meta,
                },
            )
            total = (time.perf_counter() - start_time) * 1000

            span_id = res.get("span_id")
            update_db_log(
                span_id, request_meta.get("trace_id"), {"latency_ms": int(total)}
            )

            product = ProductInDB.model_validate(res.get("data"))

            if cart_id:
                cart_db: Cart | None = await self._cart_repo.get_record(
                    id=cart_id, user_id=user_id
                )

                if not cart_db:
                    message = f"User cart not found with id {cart_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartsNotFoundError()

                cart_db.items += 1
                self._cart_repo.add(model=cart_db)
            else:
                cart_id = uuid7()
                cart = CartInDB(id=cart_id, user_id=user_id)

                self._cart_repo.add(entity=cart)
                await self._uow.flush()

            if product.quantity < cart_item.quantity:
                message = f"Product stock not enough. Id: {product_id}"
                log_error(message, request_meta)
                raise NotEnoughStockError(id=product_id)

            cart_item_db = CartItemInDB(
                cart_id=cart_id,
                product_id=product_id,
                quantity=cart_item.quantity,
                price=product.price,
                total_price=product.price * cart_item.quantity,
            )

            await self._item_service._create_cart_item(
                cart_item_db, circuit_key, request_meta
            )
            await self._uow.commit()

            cart_db: Cart | None = await self._cart_repo.get_record(
                id=cart_id, user_id=user_id
            )

            message = "Cart created successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return CartResponse.model_validate(cart_db)
        except ProductNotFoundError:
            await self._uow.rollback()

            message = f"Product not found with id: {product_id}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ProductNotFoundError(id=product_id)
        except (Exception, TimeoutError) as exc:
            await self._uow.rollback()

            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)
            elif isinstance(exc, NotEnoughStockError):
                raise NotEnoughStockError(id=cart_id)

            message = "Error occured creating cart"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def remove_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        curr_user: User,
        request_meta: dict,
        uow: UnitOfWorkRepository,
    ) -> CartResponse | list:
        await self._cart_repo.aclose()

        self._uow = uow
        self._cart_repo._async_session = self._uow.session
        self._item_service = CartItemService(
            item_repo=CartItemRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )

        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            """
            Acquire a lock on cart and cart item row to prevent concurrent modifications
            such as a deletion of the cart or removal of a cart item.

            By default, postgresql uses the read committed isolation level which
            will prevent a write-write concurrent updates on the same cart from
            seeing values that have not yet been committed.
            """

            # validate the cart exists and the current user own the cart
            cart_db: Cart | None = await self._cart_repo.get_cart_with_lock(
                False, id=cart_id, user_id=user_id
            )

            if not cart_db:
                message = f"User cart not found with id {cart_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartNotFoundError(id=cart_id)

            cart_item_db: CartItem | None = await self._item_service._get_cart_item(
                cart_id, product_id
            )

            if not cart_item_db:
                message = f"Cart item not found. Cart_id: {cart_id} - Product_id: {product_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)

            await self._item_service._delete_cart_item(
                cart_item_db, circuit_key, request_meta
            )

            if (cart_db.items - 1) < 1:
                await self._cart_repo.delete(model=cart_db)
            else:
                cart_db.items -= 1

            await self._uow.commit()

            message = (
                "Cart item removed successfully."
                f"Cart_id: {cart_id} - Product_id: {product_id}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)

            cart_db: Cart | None = await self._cart_repo.get_record(
                id=cart_id, user_id=user_id
            )

            return CartResponse.model_validate(cart_db) if cart_db else []
        except Exception as exc:
            await self._uow.rollback()

            if isinstance(exc, CartItemNotFoundError):
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)
            elif isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)

            message = (
                f"Error occured while incrementing cart item {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def increment_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        quantity: int,
        curr_user: User,
        request_meta: dict,
        uow: UnitOfWorkRepository,
    ) -> CartItemResponse:
        await self._cart_repo.aclose()

        self._uow = uow
        self._cart_repo._async_session = self._uow.session
        self._item_service = CartItemService(
            item_repo=CartItemRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )

        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            """
            Acquire a lock on cart and cart item row to prevent concurrent modifications
            such as a deletion of the cart or removal of a cart item.

            By default, postgresql uses the read committed isolation level which
            will prevent a write-write concurrent updates on the same cart from
            seeing values that have not yet been committed.
            """

            # validate the cart exists and the current user own the cart
            cart_db: Cart | None = await self._cart_repo.get_cart_with_lock(
                True, id=cart_id, user_id=user_id
            )

            if not cart_db:
                message = f"User cart not found with id {cart_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartNotFoundError(id=cart_id)

            cart_item_db: CartItem | None = await self._item_service._get_cart_item(
                cart_id, product_id
            )

            if not cart_item_db:
                message = f"Cart item not found. Cart_id: {cart_id} - Product_id: {product_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)

            cart_item_db.quantity += quantity
            cart_item_db.total_price = cart_item_db.price * cart_item_db.quantity

            await self._item_service._update_cart_item(
                cart_item_db, circuit_key, request_meta
            )
            await self._uow.commit()

            cart_items_db = await self._item_service._get_cart_with_items(
                user_id, cart_id=cart_id, product_id=product_id
            )
            cart_items = self._get_item_response(cart_items_db)

            message = (
                "Cart item quantity incremented successfully."
                f"Cart_id: {cart_id} - Product_id: {product_id}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return cart_items
        except Exception as exc:
            await self._uow.rollback()

            if isinstance(exc, CartItemNotFoundError):
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)
            elif isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)

            message = (
                f"Error occured while incrementing cart item {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def decrement_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        quantity: int,
        curr_user: User,
        request_meta: dict,
        uow: UnitOfWorkRepository,
    ) -> CartItemResponse | list:
        await self._cart_repo.aclose()

        self._uow = uow
        self._cart_repo._async_session = self._uow.session
        self._item_service = CartItemService(
            item_repo=CartItemRepository(async_session=self._uow.session),
            redis_repo=self._redis_repo,
        )

        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            """
            Acquire a lock on cart and cart item row to prevent concurrent modifications
            such as a delete on the cart row or removal of a cart item.

            By default, postgresql uses the read committed isolation level which
            will prevent a write-write concurrent updates on the same cart from
            seeing values that have not yet been committed.
            """

            # validate the current user own the cart
            cart_db: Cart | None = await self._cart_repo.get_cart_with_lock(
                False, id=cart_id, user_id=user_id
            )

            if not cart_db:
                message = f"User cart not found with id {cart_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartNotFoundError(id=cart_id)

            cart_item_db: CartItem | None = await self._item_service._get_cart_item(
                cart_id, product_id
            )

            if not cart_item_db:
                message = f"Cart item not found. Cart_id: {cart_id} - Product_id: {product_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)

            if (cart_item_db.quantity - quantity) < 1:
                # delete cart item if quantity is less than zero
                await self._item_service._delete_cart_item(
                    cart_item_db, circuit_key, request_meta
                )

                if (cart_db.items - 1) < 1:
                    await self._cart_repo.delete(model=cart_db)
                else:
                    cart_db.items -= 1
            else:
                cart_item_db.quantity -= quantity
                cart_item_db.total_price = cart_item_db.price * cart_item_db.quantity

                await self._item_service._update_cart_item(
                    cart_item_db, circuit_key, request_meta
                )

            await self._uow.commit()

            cart_items_db = await self._item_service._get_cart_with_items(
                user_id, cart_id=cart_id, product_id=product_id
            )

            if cart_items_db:
                cart_items = self._get_item_response(cart_items_db)
            else:
                cart_items = []

            message = (
                "Cart item quantity decremented successfully."
                f"Cart_id: {cart_id} - Product_id: {product_id}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return cart_items
        except Exception as exc:
            await self._uow.rollback()

            if isinstance(exc, CartItemNotFoundError):
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)
            elif isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)

            message = (
                f"Error occured while decrementing cart item {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def delete_cart(self, id: UUID, curr_user: User, request_meta: dict):
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            # acquire a lock on row to prevent concurrent modifications
            cart_db: Cart | None = await self._cart_repo.get_cart_with_lock(
                False, id=id, user_id=user_id
            )

            if not cart_db:
                message = f"User cart not found with id {id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartNotFoundError(id=id)

            await self._cart_repo.delete(model=cart_db)
            await self._cart_repo.commit()

            message = "User cart deleted successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)
            log_info(message, request_meta, circuit)
        except Exception as exc:
            await self._cart_repo.rollback()

            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=id)

            message = (
                f"Error occured while deleting cart with id {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc
