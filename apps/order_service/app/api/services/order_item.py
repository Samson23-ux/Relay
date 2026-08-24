from uuid import UUID


from shared.repo.redis import RedisRepository
from apps.order_service.app.api.repo.order_item import OrderItemRepository


class OrderItemService:
    def __init__(self, item_repo: OrderItemRepository, redis_repo: RedisRepository):
        self._item_repo = item_repo
        self._redis_repo = redis_repo

    async def _get_orders_with_items(self, user_id: UUID, sort: str | None, order: str):
        return await self._item_repo.get_orders_with_items(user_id, sort, order)

    async def _get_order_with_items(self, user_id: UUID, **filters):
        return await self._item_repo.get_order_with_items(user_id, **filters)

    async def _get_orders_for_deletion(self, user_id: UUID, **filters):
        return await self._item_repo.get_orders_for_deletion(user_id, **filters)

    async def create_order_items(self, order_items: list[dict]):
        await self._item_repo.insert_order_items(order_items)
