from shared.repo.redis import RedisRepository
from apps.order_service.app.api.repo.order_item import OrderItemRepository


class OrderItemService:
    def __init__(self, item_repo: OrderItemRepository, redis_repo: RedisRepository):
        self._item_repo = item_repo
        self._redis_repo = redis_repo
