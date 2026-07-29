from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Request, Query


from apps.product_service.app.deps import ProductService
from shared.shared_deps import CurrUserDep, RequestMetaData
from shared.schemas.response import SuccessResponse, AllSuccessResponse
from apps.product_service.app.api.schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter()


@router.get(
    "/products/{id}",
    status_code=200,
    description="Get a product by its id",
    response_model=SuccessResponse[ProductResponse],
)
async def get_product_by_id(
    id: UUID,
    request: Request,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductService,
):
    pass


# product page with cache implementation
@router.get(
    "/products",
    status_code=200,
    description="Get product page",
    response_model=SuccessResponse[ProductResponse],
)
async def get_products(
    request: Request,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductService,
):
    pass


@router.get(
    "/products/all",
    status_code=200,
    description="Get all products",
    response_model=AllSuccessResponse[ProductResponse],
)
async def get_all_products(
    request: Request,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductService,
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
    pass


@router.post(
    "/products",
    status_code=201,
    description="Create a product (Admin only).",
    response_model=SuccessResponse[ProductResponse],
)
async def create_product(
    request: Request,
    curr_user: CurrUserDep,
    product_create: ProductCreate,
    request_meta: RequestMetaData,
    product_service: ProductService,
):
    pass


@router.patch(
    "/products/{id}",
    status_code=200,
    description="Update a product (Admin only).",
    response_model=SuccessResponse[ProductResponse],
)
async def update_product(
    id: UUID,
    request: Request,
    curr_user: CurrUserDep,
    product_update: ProductUpdate,
    request_meta: RequestMetaData,
    product_service: ProductService,
):
    pass


@router.delete(
    "/products/{id}",
    status_code=204,
    description="Delete a product (Admin only).",
)
async def delete_product(
    id: UUID,
    request: Request,
    curr_user: CurrUserDep,
    request_meta: RequestMetaData,
    product_service: ProductService,
):
    pass
