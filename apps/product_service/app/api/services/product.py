import json
from uuid import UUID
from sqlalchemy import Sequence


from shared.utils import log_info, log_error
from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from apps.user_service.app.api.models.user import User
from apps.product_service.app.api.models.product import Product
from apps.product_service.app.api.repo.product import ProductRepository
from apps.product_service.app.api.schemas.product import (
    ProductInDB,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from apps.product_service.app.core.exceptions import (
    ProductExistsError,
    ProductNotFoundError,
    ProductsNotFoundError,
)


class ProductService:
    def __init__(self, product_repo: ProductRepository, redis_repo: RedisRepository):
        self._redis_repo = redis_repo
        self._product_repo = product_repo

    async def _get_product(self, name: str) -> Product | None:
        return await self._product_repo.get_record(name=name)

    async def get_products(
        self, curr_user: User, request_meta: dict
    ) -> list[ProductResponse]:
        request_meta["user_id"] = curr_user.id
        circuit_key: str = f"circuit:{request_meta.get("upstream")}"

        try:
            cached_products: str = await self._redis_repo.get_key("page:products")

            if not cached_products:
                products_db: Sequence[Product] = await self._product_repo.get_products()

                if not products_db:
                    message = "Products not found in database"
                    circuit: dict = await self._redis_repo.get_hset(circuit_key)

                    log_info(message, request_meta, circuit)
                    raise ProductsNotFoundError()

                cache_data: list[dict] = [
                    ProductInDB.model_validate(p).model_dump() for p in products_db
                ]

                for p in cache_data:
                    p["id"] = str(p["id"])
                    p["price"] = str(p["price"])
                    p["created_at"] = p["created_at"].isoformat()
                    p["updated_at"] = p["updated_at"].isoformat() if p["updated_at"] else None

                products: str = json.dumps(cache_data)
                await self._redis_repo.set_key("page:products", products)

                product_res: list[dict] = [
                    ProductResponse.model_validate(p) for p in products_db
                ]
            else:
                cached_res: list[dict] = json.loads(cached_products)
                product_res: list[ProductResponse] = [
                    ProductResponse.model_validate(p) for p in cached_res
                ]

            message = "Products retrieved successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return product_res
        except Exception as exc:
            if isinstance(exc, ProductsNotFoundError):
                raise ProductsNotFoundError()

            message = f"Error occured while retrieving products. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def get_all_products(
        self,
        curr_user: User,
        request_meta: dict,
        sort: str | None,
        limit: int | None,
        order: str | None,
        cursor: str | None,
    ) -> dict:
        request_meta["user_id"] = curr_user.id
        circuit_key: str = f"circuit:{request_meta.get("upstream")}"

        try:
            res: dict = await self._product_repo.get_records(sort, order, cursor, limit)

            products_db: Sequence[Product] = res.get("data")

            if not products_db:
                message = "Products not found in database"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_info(message, request_meta, circuit)
                raise ProductsNotFoundError()

            product_res: list[ProductResponse] = [
                ProductResponse.model_validate(p) for p in products_db
            ]

            message = "Products retrieved successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return {"data": product_res, "cursor": res.get("cursor")}
        except Exception as exc:
            if isinstance(exc, ProductsNotFoundError):
                raise ProductsNotFoundError()

            message = f"Error occured while retrieving products. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def get_product_by_id(
        self, id: UUID, curr_user: User, request_meta: dict
    ) -> ProductResponse:
        request_meta["user_id"] = curr_user.id
        circuit_key: str = f"circuit:{request_meta.get("upstream")}"

        try:
            product_db: Product | None = await self._product_repo.get_record(id=id)

            if not product_db:
                message = f"Product not found with id: {id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise ProductNotFoundError(id=id)

            message = "Product retrieved successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return ProductResponse.model_validate(product_db)
        except Exception as exc:
            if isinstance(exc, ProductNotFoundError):
                raise ProductNotFoundError(id=id)

            message = f"Error occured while retrieving product. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def create_product(
        self, curr_user: User, request_meta: dict, product_create: ProductCreate
    ) -> ProductResponse:
        request_meta["user_id"] = curr_user.id
        product_name: str = product_create.name
        circuit_key: str = f"circuit:{request_meta.get("upstream")}"

        product_exists: Product | None = await self._get_product(product_name)

        if product_exists:
            message = f"Product already exists with name: {product_name}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ProductExistsError(name=product_name)

        try:
            self._product_repo.add(entity=product_create)
            await self._product_repo.commit()

            product: Product = await self._get_product(product_name)

            message = "Product created successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return ProductResponse.model_validate(product)
        except Exception as exc:
            await self._product_repo.rollback()

            message = f"Error occured while creating product. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def update_product(
        self,
        id: UUID,
        curr_user: User,
        request_meta: dict,
        product_update: ProductUpdate,
    ) -> ProductResponse:
        request_meta["user_id"] = curr_user.id
        circuit_key: str = f"circuit:{request_meta.get("upstream")}"

        try:
            product_db: Product | None = await self._product_repo.get_record(id=id)

            if not product_db:
                message = f"Product not found with id: {id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise ProductNotFoundError(id=id)

            product_update_dict: dict = product_update.model_dump(exclude_unset=True)

            for k, v in product_update_dict.items():
                setattr(product_db, k, v)

            self._product_repo.add(model=product_db)
            await self._product_repo.commit()

            product: Product = await self._get_product(product_db.name)

            message = "Product updated successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
            return ProductResponse.model_validate(product)
        except Exception as exc:
            await self._product_repo.rollback()

            if isinstance(exc, ProductNotFoundError):
                raise ProductNotFoundError(id=id)

            message = f"Error occured while updating product. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc

    async def delete_product(
        self,
        id: UUID,
        curr_user: User,
        request_meta: dict,
    ):
        request_meta["user_id"] = curr_user.id
        circuit_key: str = f"circuit:{request_meta.get("upstream")}"

        try:
            product_db: Product | None = await self._product_repo.get_record(id=id)

            if not product_db:
                message = f"Product not found with id: {id}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise ProductNotFoundError(id=id)

            await self._product_repo.delete(model=product_db)
            await self._product_repo.commit()

            message = "Product deleted successfully"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
        except Exception as exc:
            await self._product_repo.rollback()

            if isinstance(exc, ProductNotFoundError):
                raise ProductNotFoundError(id=id)

            message = f"Error occured while deleting product. Error: {str(exc)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from exc
