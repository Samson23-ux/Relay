from shared.repo.redis import RedisRepository
from apps.product_service.app.api.repo.product import ProductRepository


class ProductService:
    def __init__(self, product_repo: ProductRepository, redis_repo: RedisRepository):
        self._redis_repo = redis_repo
        self._product_repo = product_repo
