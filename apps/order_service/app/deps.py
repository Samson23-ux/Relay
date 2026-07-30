from typing import Annotated
from fastapi import Depends, Request


from shared.shared_deps import DBSession
from shared.services.request import Request as HTTPRequest
from apps.order_service.app.api.repo.cart import CartRepository
from apps.order_service.app.api.services.cart import CartService


# ----------------- repo dependency ------------------- #
async def get_cart_repo(session: DBSession) -> CartRepository:
    return CartRepository(async_session=session)


CartRepo = Annotated[CartRepository, Depends(get_cart_repo)]


# ------------------ service dependency --------------- #
async def get_cart_service(cart_repo: CartRepo) -> CartService:
    return CartService(cart_repo=cart_repo)


async def get_request_service(request: Request) -> HTTPRequest:
    client = request.app.state.client
    return HTTPRequest(async_client=client)


CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
HTTPRequestDep = Annotated[HTTPRequest, Depends(get_request_service)]
