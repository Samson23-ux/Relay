from typing import Annotated
from fastapi import Depends, Request


from shared.shared_deps import DBSession, RedisRepo
from apps.order_service.app.api.repo.cart import CartRepository
from apps.order_service.app.api.services.cart import CartService
from apps.order_service.app.api.repo.cart_item import CartItemRepository
from apps.order_service.app.api.services.cart_item import CartItemService


# ----------------- repo dependency ------------------- #
async def get_cart_repo(session: DBSession) -> CartRepository:
    return CartRepository(async_session=session)


async def get_cart_item_repo(session: DBSession) -> CartItemRepository:
    return CartItemRepository(async_session=session)


CartRepo = Annotated[CartRepository, Depends(get_cart_repo)]
CartItemRepo = Annotated[CartRepository, Depends(get_cart_item_repo)]


# ------------------ service dependency --------------- #
async def get_cart_service(cart_repo: CartRepo, redis_repo: RedisRepo) -> CartService:
    return CartService(cart_repo=cart_repo, redis_repo=redis_repo)


async def get_cart_item_service(
    item_repo: CartItemRepo, redis_repo: RedisRepo
) -> CartItemService:
    return CartItemService(item_repo=item_repo, redis_repo=redis_repo)


CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
CartItemServiceDep = Annotated[CartItemService, Depends(get_cart_item_service)]
