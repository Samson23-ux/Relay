from uuid import UUID
from sqlalchemy import func, select, Sequence


from shared.repo.base_repo import BaseRepository
from apps.product_service.app.api.models.product import Product
from apps.product_service.app.api.schemas.product import ProductBase
from apps.product_service.app.api.models.product_reserve import ProductReserve


class ProductRepository(BaseRepository[ProductBase, Product]):
    model = Product

    def _entity_to_model(self, entity):
        return Product(**entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "id" in filters:
            filter_conditions.append(self.model.id == filters["id"])
        if "name" in filters:
            filter_conditions.append(
                func.lower(self.model.name) == filters["name"].lower()
            )
        return filter_conditions

    def _get_sort_fields(self, sort):
        sort_fields = []
        sortable_fields: dict = {
            "price": self.model.price,
            "quantity": self.model.quantity,
            "created_at": self.model.created_at,
        }

        sort_fields.append(sortable_fields.get(sort, self.model.created_at))
        return sort_fields

    async def get_products(self, limit: int = 15) -> Sequence[Product]:
        res = await self._async_session.execute(select(self.model).limit(limit))
        return res.scalars().all()

    async def get_products_by_ids(self, ids: list[UUID]) -> Sequence[Product]:
        res = await self._async_session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return res.scalars().all()

    def get_product_with_lock(self, read: bool, id: UUID) -> Product | None:
        base_stmt = select(self.model).where(self.model.id == id)

        if read:
            base_stmt = base_stmt.with_for_update(read=True)
        else:
            base_stmt = base_stmt.with_for_update()

        res = self._sync_session.execute(base_stmt)
        return res.scalar()

    def get_product_total_reserve(self, product_id: UUID) -> int | None:
        stmt = (
            select(func.sum(ProductReserve.reserve))
            .select_from(self.model)
            .join(ProductReserve)
            .where(self.model.id == product_id)
        )
        res = self._sync_session.execute(stmt)
        return res.scalar()
