from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Query


from apps.product_service.app.deps import ProductServiceDep
from shared.shared_deps import CurrUserDep, RequestMetaData
from shared.schemas.response import SuccessResponse, AllSuccessResponse
from apps.product_service.app.api.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

router = APIRouter()


# product page with cache implementation
@router.get(
    "/products",
    status_code=200,
    description="Get product page",
    response_model=SuccessResponse[ProductResponse],
)
async def get_products(
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
):
    products: list[ProductResponse] = await product_service.get_products(
        curr_user, request_meta
    )
    return SuccessResponse(
        message="Page products retrieved successfully", data=products
    )


@router.get(
    "/products/all",
    status_code=200,
    description="Get all products",
    response_model=AllSuccessResponse[ProductResponse],
)
async def get_all_products(
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
    cursor: Annotated[
        str,
        Query(description="Cursor of last received product batch. None if first fetch"),
    ] = None,
    sort: Annotated[
        str, Query(description="Sort products by price/quantity/created_at")
    ] = None,
    limit: Annotated[
        int, Query(description="Limit the number of products returned")
    ] = 10,
    order: Annotated[
        str, Query(description="Order products in ascending(asc) or descending(desc)")
    ] = "asc",
):
    res: dict = await product_service.get_all_products(
        curr_user, request_meta, sort, limit, order, cursor
    )

    cursor: str = res.get("cursor")
    products: list[ProductResponse] = res.get("data")

    return AllSuccessResponse(
        message="Products retrieved successfully", data=products, cursor=cursor
    )


@router.get(
    "/products/{id}",
    status_code=200,
    description="Get a product by its id",
    response_model=SuccessResponse[ProductResponse],
)
async def get_product_by_id(
    id: UUID,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
):
    product: ProductResponse = await product_service.get_product_by_id(
        id, curr_user, request_meta
    )
    return SuccessResponse(message="Product retrieved successfully", data=product)


@router.patch(
    "/products/{id}/reserve",
    status_code=200,
    description="Reserve a product for orders and cart",
    response_model=SuccessResponse[ProductResponse],
)
async def reserve_product(
    id: UUID,
    curr_user: CurrUserDep,
    quantity: Annotated[int, Query(..., ge=1)],
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
):
    product: ProductResponse = await product_service.reserve_product(
        id, quantity, curr_user, request_meta
    )
    return SuccessResponse(message="Product reserved successfully", data=product)


@router.post(
    "/products",
    status_code=201,
    description="Create a product (Admin only).",
    response_model=SuccessResponse[ProductResponse],
)
async def create_product(
    curr_user: CurrUserDep,
    product_create: ProductCreate,
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
):
    product: ProductResponse = await product_service.create_product(
        curr_user, request_meta, product_create
    )
    return SuccessResponse(message="Product created successfully", data=product)


@router.patch(
    "/products/{id}",
    status_code=200,
    description="Update a product (Admin only).",
    response_model=SuccessResponse[ProductResponse],
)
async def update_product(
    id: UUID,
    curr_user: CurrUserDep,
    product_update: ProductUpdate,
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
):
    product: ProductResponse = await product_service.update_product(
        id, curr_user, request_meta, product_update
    )
    return SuccessResponse(message="Product updated successfully", data=product)


@router.delete(
    "/products/{id}",
    status_code=204,
    description="Delete a product (Admin only).",
)
async def delete_product(
    id: UUID,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductServiceDep,
):
    await product_service.delete_product(id, curr_user, request_meta)
