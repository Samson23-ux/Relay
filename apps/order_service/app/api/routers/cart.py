from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Query


from shared.schemas.response import SuccessResponse
from apps.order_service.app.api.schemas.cart_item import CartItemResponse
from apps.order_service.app.deps import CartServiceDep, CartItemServiceDep
from apps.order_service.app.api.schemas.cart import CartResponse, AddToCart
from shared.shared_deps import CurrUserDep, RequestMetaData

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
    cart_item_service: CartItemServiceDep,
    items: Annotated[bool, Query(description="Return carts with items.")] = False,
    sort: Annotated[str, Query(description="Sort by created_at")] = None,
    order: Annotated[str, Query(description="Order result in asc or desc")] = "asc",
):
    carts: list[CartResponse | CartItemResponse] = await cart_service.get_carts(
        items, curr_user, order, sort, request_meta, cart_item_service
    )
    return SuccessResponse(message="Carts retrieved successfully", data=carts)


@router.get(
    "/carts/{id}",
    status_code=200,
    response_model=SuccessResponse[CartResponse | CartItemResponse],
    description="Get cart by id",
)
async def get_cart_by_id(
    id: UUID,
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
    cart_item_service: CartItemServiceDep,
    items: Annotated[bool, Query(description="Return cart with items.")] = False,
):
    cart: CartResponse | list[CartItemResponse] = await cart_service.get_cart_by_id(
        id, items, curr_user, request_meta, cart_item_service
    )
    return SuccessResponse(message="Cart retrieved successfully", data=cart)


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
    cart_id: Annotated[UUID, Query(description="Id of an existing cart")] = None,
):
    cart: CartResponse = await cart_service.create_cart(
        curr_user, request_meta, cart_item, cart_id
    )
    return SuccessResponse(message="Cart created successfully", data=cart)


@router.patch(
    "/carts/{cart_id}/products/{product_id}/remove",
    status_code=200,
    response_model=SuccessResponse[CartResponse | list],
    description="Remove item from cart. Cart gets deleted if there are no more items",
)
async def remove_cart_item(
    cart_id: UUID,
    product_id: UUID,
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
):
    cart: CartResponse | list = await cart_service.remove_item(
        cart_id, product_id, curr_user, request_meta
    )
    return SuccessResponse(message="Cart item removed successfully", data=cart)


@router.patch(
    "/carts/{cart_id}/products/{product_id}/increment",
    status_code=200,
    response_model=SuccessResponse[CartItemResponse],
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
    cart_items: CartItemResponse = await cart_service.increment_item(
        cart_id, product_id, quantity, curr_user, request_meta
    )
    return SuccessResponse(
        message="Cart item incremented successfully", data=cart_items
    )


@router.patch(
    "/carts/{cart_id}/products/{product_id}/decrement",
    status_code=200,
    response_model=SuccessResponse[CartItemResponse | list],
    description=(
        "Decrement a product in a cart."
        "The cart item is deleted if the quantity falls below 1."
        "Cart gets deleted if there are no more items"
    ),
)
async def decrement_cart_item(
    cart_id: UUID,
    product_id: UUID,
    quantity: Annotated[int, Query(..., description="Quantity of product")],
    curr_user: CurrUserDep,
    cart_service: CartServiceDep,
    request_meta: RequestMetaData,
):
    cart_items: CartItemResponse | list = await cart_service.decrement_item(
        cart_id, product_id, quantity, curr_user, request_meta
    )
    return SuccessResponse(
        message="Cart item decremented successfully", data=cart_items
    )


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
    await cart_service.delete_cart(id, curr_user, request_meta)
