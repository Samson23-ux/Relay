from fastapi import Depends
from typing import Annotated


from shared.shared_deps import DBSession, RedisRepo
from apps.product_service.app.api.repo.product import ProductRepository
from apps.product_service.app.api.services.product import ProductService
from apps.product_service.app.api.repo.product_reserve import ProductReserveRepository


# ----------------- repo dependency ------------------- #
async def get_product_repo(session: DBSession) -> ProductRepository:
    return ProductRepository(async_session=session)


async def get_reserve_repo(session: DBSession) -> ProductReserveRepository:
    return ProductReserveRepository(async_session=session)


ProductRepo = Annotated[ProductRepository, Depends(get_product_repo)]
ReserveRepo = Annotated[ProductReserveRepository, Depends(get_reserve_repo)]


# ------------------ service dependency --------------- #
async def get_product_service(
    product_repo: ProductRepo, reserve_repo: ReserveRepo, redis_repo: RedisRepo
) -> ProductService:
    return ProductService(
        product_repo=product_repo, reserve_repo=reserve_repo, redis_repo=redis_repo
    )


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
