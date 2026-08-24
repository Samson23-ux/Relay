from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Query


from shared.schemas.response import SuccessResponse
from apps.order_service.app.api.schemas.order import OrderResponse
from apps.order_service.app.api.schemas.order_item import OrderItemResponse
from shared.shared_deps import CurrUserDep, RequestMetaData, UnitOfWorkRepo
from apps.order_service.app.api.schemas.order_item import OrderItemResponse
from apps.order_service.app.deps import OrderServiceDep, OrderItemServiceDep

router = APIRouter()


@router.get(
    "/orders",
    status_code=200,
    response_model=SuccessResponse[OrderResponse | OrderItemResponse],
    description="Get user orders",
)
async def get_orders(
    curr_user: CurrUserDep,
    order_service: OrderServiceDep,
    request_meta: RequestMetaData,
    order_item_service: OrderItemServiceDep,
    items: Annotated[bool, Query(description="Return orders with items.")] = False,
    sort: Annotated[str, Query(description="Sort by created_at")] = None,
    order: Annotated[str, Query(description="Order result in asc or desc")] = "asc",
):
    orders: list[OrderResponse | OrderItemResponse] = await order_service.get_orders(
        items, curr_user, order, sort, request_meta, order_item_service
    )
    return SuccessResponse(message="Orders retrieved successfully", data=orders)


@router.get(
    "/orders/{id}",
    status_code=200,
    response_model=SuccessResponse[OrderResponse | OrderItemResponse],
    description="Get order by id",
)
async def get_order_by_id(
    id: UUID,
    curr_user: CurrUserDep,
    order_service: OrderServiceDep,
    request_meta: RequestMetaData,
    order_item_service: OrderItemServiceDep,
    items: Annotated[bool, Query(description="Return order with items.")] = False,
):
    order: OrderResponse | list[OrderItemResponse] = await order_service.get_order_id(
        id, items, curr_user, request_meta, order_item_service
    )
    return SuccessResponse(message="Order retrieved successfully", data=order)


@router.post(
    "/orders",
    status_code=201,
    response_model=SuccessResponse[OrderResponse],
    description="Create an order with cart_id",
)
async def create_order(
    uow: UnitOfWorkRepo,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    order_service: OrderServiceDep,
    cart_id: Annotated[UUID, Query(..., description="Id of an existing cart")],
):
    order: OrderResponse = await order_service.create_order(
        cart_id, curr_user, request_meta, uow
    )
    return SuccessResponse(message="Order created successfully", data=order)


@router.delete(
    "/orders/{id}",
    status_code=204,
    description="Delete order by id",
)
async def delete_order(
    id: UUID,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    order_service: OrderServiceDep,
    order_item_service: OrderItemServiceDep,
):
    await order_service.delete_order(id, curr_user, request_meta, order_item_service)
