from shared.repo.redis import RedisRepository
from apps.order_service.app.api.repo.order import OrderRepository


class OrderService:
    def __init__(self, order_repo: OrderRepository, redis_repo: RedisRepository):
        self._uow = None
        self._item_service = None
        self._order_repo = order_repo
        self._redis_repo = redis_repo
