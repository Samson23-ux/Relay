from decimal import Decimal
from uuid import UUID, uuid7


from shared.repo.redis import RedisRepository
from shared.utils import log_info, log_error
from apps.user_service.app.api.models.user import User
from apps.order_service.app.api.repo.cart import CartRepository
from shared.core.exceptions import ServerError, ServiceUnavailable
from apps.product_service.app.api.schemas.product import ProductItem
from apps.order_service.app.api.services.cart_item import CartItemService
from apps.order_service.app.api.schemas.cart import CartResponse, AddToCart, CartInDB
from apps.order_service.app.api.schemas.cart_item import CartItemResponse, CartItemInDB
from apps.order_service.app.utils import (
    fetch_product,
    get_items_response,
    serialize_cart,
    serialize_cart_item,
)
from apps.product_service.app.core.exceptions import (
    NotEnoughStockError,
    ProductNotFoundError,
    TaskProductNotFoundError,
)
from apps.order_service.app.core.exceptions import (
    CartNotFoundError,
    CartsNotFoundError,
    CartItemNotFoundError,
)


class CartService:
    def __init__(
        self,
        cart_repo: CartRepository,
        redis_repo: RedisRepository,
    ):
        self._cart_repo = cart_repo
        self._redis_repo = redis_repo
        self._item_service = CartItemService(cart_repo=cart_repo, redis_repo=redis_repo)

    def _get_item_response(self, items: list[tuple]):
        (item,) = items
        product = ProductItem(
            product_id=item[0], name=item[1], description=item[2], serial=item[3]
        )
        cart_item = CartItemResponse(
            product=product,
            quantity=item[4],
            price=item[5],
            total_price=item[6],
            created_at=item[7],
            cart_id=item[8],
        )

        return cart_item

    async def _get_cart(self, request_meta: dict, **filters) -> dict:
        cart_id: UUID = filters.get("id")
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            user_id = filters.get("user_id")
            cart: dict | None = await self._cart_repo.get_cart(cart_id)

            if not cart or (user_id and cart["user_id"] != str(user_id)):
                message = f"Cart not found with id {cart_id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise CartNotFoundError(id=cart_id)
            return cart
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
                    user_id, sort, order, request_meta
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
                carts_db: list[dict] = await self._cart_repo.get_carts(
                    user_id, sort, order
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
                cart_db = await cart_item_service._get_cart_with_items(
                    user_id, cart_id=id, request_meta=request_meta
                )

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
                cart_db: dict | None = await self._cart_repo.get_cart(id)

                if not cart_db or cart_db["user_id"] != str(user_id):
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
    ) -> CartResponse:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        product_id: UUID = cart_item.product_id

        try:
            product = await fetch_product(product_id, request_meta)

            if product.quantity < cart_item.quantity:
                message = f"Product stock not enough. Id: {product_id}"
                log_error(message, request_meta)
                raise NotEnoughStockError(id=product_id)

            existing_cart_id = cart_id is not None
            if not existing_cart_id:
                cart_id = uuid7()

            item_entity = CartItemInDB(
                product_id=product_id,
                quantity=cart_item.quantity,
                price=product.price,
                total_price=product.price * cart_item.quantity,
            )

            if existing_cart_id:
                token = await self._cart_repo.acquire_lock(cart_id)
                try:
                    cart: dict | None = await self._cart_repo.get_cart(cart_id)

                    if not cart or cart["user_id"] != str(user_id):
                        message = f"User cart not found with id {cart_id}"
                        circuit: dict = await self._redis_repo.get_hset(circuit_key)

                        log_error(message, request_meta, circuit)
                        raise CartNotFoundError(id=cart_id)

                    existing_prd_ids = {
                        item["product_id"] for item in cart["cart_items"]
                    }
                    if str(product_id) not in existing_prd_ids:
                        cart["cart_items"].append(serialize_cart_item(item_entity))
                        cart["items"] += 1
                    await self._cart_repo.save_cart(cart)
                finally:
                    await self._cart_repo.release_lock(cart_id, token)
            else:
                cart_entity = CartInDB(
                    id=cart_id,
                    user_id=user_id,
                    items=1,
                    cart_items=[item_entity],
                )
                cart = serialize_cart(cart_entity)

                await self._cart_repo.save_cart(cart)
                await self._cart_repo.index_cart(
                    user_id, cart_id, cart_entity.created_at.timestamp()
                )

            message = "Cart created successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return CartResponse.model_validate(cart)
        except TaskProductNotFoundError:
            message = f"Product not found with id: {product_id}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ProductNotFoundError(id=product_id)
        except Exception as exc:
            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)
            elif isinstance(exc, NotEnoughStockError):
                raise NotEnoughStockError(id=product_id)

            message = "Error occured creating cart"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)

            if isinstance(exc, ServiceUnavailable):
                raise ServiceUnavailable() from exc
            raise ServerError() from exc

    async def remove_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        curr_user: User,
        request_meta: dict,
    ) -> CartResponse | list:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            token = await self._cart_repo.acquire_lock(cart_id)
            try:
                cart: dict | None = await self._cart_repo.get_cart(cart_id)

                if not cart or cart["user_id"] != str(user_id):
                    message = f"User cart not found with id {cart_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartNotFoundError(id=cart_id)

                cart_item = next(
                    (
                        item
                        for item in cart["cart_items"]
                        if item["product_id"] == str(product_id)
                    ),
                    None,
                )

                if not cart_item:
                    message = f"Cart item not found. Cart_id: {cart_id} - Product_id: {product_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)

                cart["cart_items"].remove(cart_item)

                if (cart["items"] - 1) < 1:
                    await self._cart_repo.delete_cart(user_id, cart_id)
                    cart = None
                else:
                    cart["items"] -= 1
                    await self._cart_repo.save_cart(cart)
            finally:
                await self._cart_repo.release_lock(cart_id, token)

            message = (
                "Cart item removed successfully."
                f"Cart_id: {cart_id} - Product_id: {product_id}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return CartResponse.model_validate(cart) if cart else []
        except Exception as exc:
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
    ) -> CartItemResponse:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            token = await self._cart_repo.acquire_lock(cart_id)
            try:
                cart: dict | None = await self._cart_repo.get_cart(cart_id)

                if not cart or cart["user_id"] != str(user_id):
                    message = f"User cart not found with id {cart_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartNotFoundError(id=cart_id)

                cart_item = next(
                    (
                        item
                        for item in cart["cart_items"]
                        if item["product_id"] == str(product_id)
                    ),
                    None,
                )

                if not cart_item:
                    message = f"Cart item not found. Cart_id: {cart_id} - Product_id: {product_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)

                new_quantity = cart_item["quantity"] + quantity
                product = await fetch_product(product_id, request_meta)

                if product.quantity < new_quantity:
                    message = f"Product stock not enough. Id: {product_id}"
                    log_error(message, request_meta)
                    raise NotEnoughStockError(id=product_id)

                cart_item["quantity"] = new_quantity
                cart_item["total_price"] = str(
                    Decimal(cart_item["price"]) * cart_item["quantity"]
                )

                await self._cart_repo.save_cart(cart)
            finally:
                await self._cart_repo.release_lock(cart_id, token)

            cart_items_db = await self._item_service._get_cart_with_items(
                user_id,
                cart_id=cart_id,
                product_id=product_id,
                request_meta=request_meta,
            )
            cart_items = self._get_item_response(cart_items_db)

            message = (
                "Cart item quantity incremented successfully."
                f"Cart_id: {cart_id} - Product_id: {product_id}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return cart_items
        except TaskProductNotFoundError:
            message = f"Product not found with id: {product_id}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ProductNotFoundError(id=product_id)
        except Exception as exc:
            if isinstance(exc, CartItemNotFoundError):
                raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)
            elif isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=cart_id)
            elif isinstance(exc, NotEnoughStockError):
                raise NotEnoughStockError(id=product_id)

            message = (
                f"Error occured while incrementing cart item {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)

            if isinstance(exc, ServiceUnavailable):
                raise ServiceUnavailable() from exc
            raise ServerError() from exc

    async def decrement_item(
        self,
        cart_id: UUID,
        product_id: UUID,
        quantity: int,
        curr_user: User,
        request_meta: dict,
    ) -> CartItemResponse | list:
        user_id: UUID = curr_user.id
        request_meta["user_id"] = user_id
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        try:
            token = await self._cart_repo.acquire_lock(cart_id)
            try:
                cart: dict | None = await self._cart_repo.get_cart(cart_id)

                if not cart or cart["user_id"] != str(user_id):
                    message = f"User cart not found with id {cart_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartNotFoundError(id=cart_id)

                cart_item = next(
                    (
                        item
                        for item in cart["cart_items"]
                        if item["product_id"] == str(product_id)
                    ),
                    None,
                )

                if not cart_item:
                    message = f"Cart item not found. Cart_id: {cart_id} - Product_id: {product_id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartItemNotFoundError(cart_id=cart_id, product_id=product_id)

                if (cart_item["quantity"] - quantity) < 1:
                    # delete cart item if quantity is less than zero
                    cart["cart_items"].remove(cart_item)

                    if (cart["items"] - 1) < 1:
                        await self._cart_repo.delete_cart(user_id, cart_id)
                        cart = None
                    else:
                        cart["items"] -= 1
                        await self._cart_repo.save_cart(cart)
                else:
                    cart_item["quantity"] -= quantity
                    cart_item["total_price"] = str(
                        Decimal(cart_item["price"]) * cart_item["quantity"]
                    )

                    await self._cart_repo.save_cart(cart)
            finally:
                await self._cart_repo.release_lock(cart_id, token)

            cart_items_db = await self._item_service._get_cart_with_items(
                user_id,
                cart_id=cart_id,
                product_id=product_id,
                request_meta=request_meta,
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
            token = await self._cart_repo.acquire_lock(id)
            try:
                cart: dict | None = await self._cart_repo.get_cart(id)

                if not cart or cart["user_id"] != str(user_id):
                    message = f"User cart not found with id {id}"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_error(message, request_meta, circuit)
                    raise CartNotFoundError(id=id)

                await self._cart_repo.delete_cart(user_id, id)
            finally:
                await self._cart_repo.release_lock(id, token)

            message = "User cart deleted successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)
            log_info(message, request_meta, circuit)
        except Exception as exc:
            if isinstance(exc, CartNotFoundError):
                raise CartNotFoundError(id=id)

            message = (
                f"Error occured while deleting cart with id {id}. Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def _delete_cart(self, id: UUID, user_id: UUID):
        token = await self._cart_repo.acquire_lock(id)
        try:
            await self._cart_repo.delete_cart(user_id, id)
        finally:
            await self._cart_repo.release_lock(id, token)
