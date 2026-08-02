from uuid import UUID


from shared.utils import log_error
from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from apps.order_service.app.api.models.cart_item import CartItem
from apps.order_service.app.api.schemas.cart_item import CartItemInDB
from apps.order_service.app.api.repo.cart_item import CartItemRepository


class CartItemService:
    def __init__(self, item_repo: CartItemRepository, redis_repo: RedisRepository):
        self._item_repo = item_repo
        self._redis_repo = redis_repo

    async def _get_carts_items(self, user_id: UUID):
        return await self._item_repo.get_carts_with_items(user_id)

    async def _get_cart_items(self, user_id: UUID, **filters):
        return await self._item_repo.get_cart_with_items(
            user_id, **filters
        )

    async def _get_cart_item(self, cart_id: UUID, product_id: UUID) -> CartItem | None:
        return await self._item_repo.get_cart_item(
            cart_id=cart_id, product_id=product_id
        )

    async def _create_cart_item(
        self, cart_item: CartItemInDB, circuit_key: str, request_meta: dict
    ):
        try:
            await self._item_repo.insert_cart_item(entity=cart_item)
        except Exception as exc:
            message = (
                "Error occured while creating cart item."
                f"Cart_id: {cart_item.cart_id} - Product_id: {cart_item.product_id}."
                f"Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def _update_cart_item(
        self, cart_item: CartItem, circuit_key: str, request_meta: dict
    ):
        try:
            self._item_repo.add(model=cart_item)
        except Exception as exc:
            message = (
                "Error occured while updating cart item."
                f"Cart_id: {cart_item.cart_id} - Product_id: {cart_item.product_id}."
                f"Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def _delete_cart_item(
        self, cart_item: CartItem, circuit_key: str, request_meta: dict
    ):
        try:
            await self._item_repo.delete(model=cart_item)
        except Exception as exc:
            message = (
                "Error occured while deleting cart item."
                f"Cart_id: {cart_item.cart_id} - Product_id: {cart_item.product_id}."
                f"Error: {str(exc)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc
