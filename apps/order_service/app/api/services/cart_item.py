from uuid import UUID


from shared.repo.redis import RedisRepository
from apps.order_service.app.utils import fetch_product
from apps.order_service.app.api.repo.cart import CartRepository


class CartItemService:
    def __init__(
        self,
        cart_repo: CartRepository,
        redis_repo: RedisRepository,
    ):
        self._cart_repo = cart_repo
        self._redis_repo = redis_repo

    async def _get_cart_with_items(
        self,
        user_id: UUID,
        cart_id: UUID,
        request_meta: dict,
        product_id: UUID | None = None,
    ) -> list[tuple]:
        cart: dict | None = await self._cart_repo.get_cart(cart_id)

        if not cart or cart["user_id"] != str(user_id):
            return []

        items: list[dict] = cart["cart_items"]

        if product_id:
            items = [item for item in items if item["product_id"] == str(product_id)]

        return await self._build_item_rows(
            [(cart["id"], item) for item in items], request_meta
        )

    async def _get_carts_with_items(
        self, user_id: UUID, sort: str | None, order: str, request_meta: dict
    ) -> list[tuple]:
        carts: list[dict] = await self._cart_repo.get_carts(user_id, sort, order)
        items: list[tuple[str, dict]] = [
            (cart["id"], item) for cart in carts for item in cart["cart_items"]
        ]

        return await self._build_item_rows(items, request_meta)

    async def _build_item_rows(
        self, items: list[tuple[str, dict]], request_meta: dict
    ) -> list[tuple]:
        if not items:
            return []

        product_ids: set[str] = {item["product_id"] for _, item in items}
        products_by_id: dict = {
            product_id: await fetch_product(UUID(product_id), request_meta)
            for product_id in product_ids
        }

        rows = []
        for cart_id, item in items:
            product = products_by_id.get(item["product_id"])
            rows.append(
                (
                    product.id,
                    product.name,
                    product.description,
                    product.serial,
                    item["quantity"],
                    item["price"],
                    item["total_price"],
                    item["created_at"],
                    cart_id,
                )
            )
        return rows
