from uuid import UUID
from fastapi import APIRouter, Query
from typing import Annotated, Optional


from shared.shared_deps import CurrUserDep, RequestMetaData
from apps.order_service.app.deps import HTTPRequestDep, CartServiceDep
from shared.schemas.response import SuccessResponse, AllSuccessResponse
from apps.order_service.app.api.schemas.cart_items import CartItemResponse
from apps.order_service.app.api.schemas.cart import CartResponse, AddToCart

router = APIRouter()


@router.get(
    "/carts",
    status_code=200,
    response_model=SuccessResponse[CartResponse | CartItemResponse],
    description="Get user carts",
)
async def get_carts(
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
    items: Annotated[bool, Query(description="Return cart with items.")] = False,
):
    pass


@router.get(
    "/carts/{id}",
    status_code=200,
    response_model=SuccessResponse[CartResponse | CartItemResponse],
    description="Get cart by id",
)
async def get_cart_by_id(
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
    items: Annotated[bool, Query(description="Return cart with items.")] = False,
):
    pass


@router.post(
    "/carts",
    status_code=201,
    response_model=SuccessResponse[CartResponse],
    description="Create a new cart or add to an existing cart by providing its id",
)
async def create_cart(
    cart_item: AddToCart,
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
    request_service: HTTPRequestDep,
    cart_id: Annotated[UUID, Query(description="Id of an existing cart")] = None,
):
    pass


@router.patch(
    "/carts/{cart_id}/products/{product_id}/increment",
    status_code=200,
    response_model=SuccessResponse[CartResponse],
    description="Increment a product in a cart",
)
async def increment_cart_item(
    cart_id: UUID,
    product_id: UUID,
    quantity: Annotated[int, Query(..., description="Quantity of product")],
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
):
    pass


@router.patch(
    "/carts/{cart_id}/products/{product_id}/decrement",
    status_code=200,
    response_model=SuccessResponse[CartResponse],
    description="Decrement a product in a cart",
)
async def decrement_cart_item(
    cart_id: UUID,
    product_id: UUID,
    quantity: Annotated[int, Query(..., description="Quantity of product")],
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
):
    pass


@router.delete(
    "/carts/{id}",
    status_code=204,
    description="Delete cart by id",
)
async def delete_cart(
    id: UUID,
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
):
    pass
