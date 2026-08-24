from shared.repo.redis import RedisRepository
from shared.repo.uow import UnitOfWorkRepository
from shared.worker.db import get_db_session, get_redis_client


def get_uow():
    session = next(get_db_session())
    return UnitOfWorkRepository(sync_session=session)


def get_product_service():
    from apps.product_service.app.api.repo.product import ProductRepository
    from apps.product_service.app.api.services.product import ProductService
    from apps.product_service.app.api.repo.product_reserve import (
        ProductReserveRepository,
    )

    redis = next(get_redis_client())
    session = next(get_db_session())

    return ProductService(
        product_repo=ProductRepository(sync_session=session),
        redis_repo=RedisRepository(sync_redis=redis),
        reserve_repo=ProductReserveRepository(sync_session=session),
    )
