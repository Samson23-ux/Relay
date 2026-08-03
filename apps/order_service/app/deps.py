from fastapi import Depends
from typing import Annotated


from shared.shared_deps import DBSession, RedisRepo
from apps.order_service.app.api.repo.cart import CartRepository
from apps.order_service.app.api.services.cart import CartService
from apps.order_service.app.api.repo.order import OrderRepository
from apps.order_service.app.api.services.order import OrderService
from apps.order_service.app.api.repo.cart_item import CartItemRepository
from apps.order_service.app.api.services.cart_item import CartItemService
from apps.order_service.app.api.repo.order_item import OrderItemRepository
from apps.order_service.app.api.services.order_item import OrderItemService


# ----------------- repo dependency ------------------- #
async def get_cart_repo(session: DBSession) -> CartRepository:
    return CartRepository(async_session=session)


async def get_cart_item_repo(session: DBSession) -> CartItemRepository:
    return CartItemRepository(async_session=session)


async def get_order_repo(session: DBSession) -> OrderRepository:
    return OrderRepository(async_session=session)


async def get_order_item_repo(session: DBSession) -> OrderItemRepository:
    return OrderItemRepository(async_session=session)


CartRepo = Annotated[CartRepository, Depends(get_cart_repo)]
OrderRepo = Annotated[OrderRepository, Depends(get_order_repo)]
CartItemRepo = Annotated[CartItemRepository, Depends(get_cart_item_repo)]
OrderItemRepo = Annotated[OrderItemRepository, Depends(get_order_item_repo)]


# ------------------ service dependency --------------- #
async def get_cart_service(cart_repo: CartRepo, redis_repo: RedisRepo) -> CartService:
    return CartService(cart_repo=cart_repo, redis_repo=redis_repo)


async def get_cart_item_service(
    item_repo: CartItemRepo, redis_repo: RedisRepo
) -> CartItemService:
    return CartItemService(item_repo=item_repo, redis_repo=redis_repo)


async def get_order_service(order_repo: OrderRepo, redis_repo: RedisRepo) -> OrderService:
    return OrderService(order_repo=order_repo, redis_repo=redis_repo)


async def get_order_item_service(
    item_repo: OrderItemRepo, redis_repo: RedisRepo
) -> OrderItemService:
    return OrderItemService(item_repo=item_repo, redis_repo=redis_repo)


CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
CartItemServiceDep = Annotated[CartItemService, Depends(get_cart_item_service)]
OrderItemServiceDep = Annotated[OrderItemService, Depends(get_order_item_service)]
