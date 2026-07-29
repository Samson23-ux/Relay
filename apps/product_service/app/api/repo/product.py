from sqlalchemy import func, select, Sequence


from shared.repo.base_repo import BaseRepository
from apps.product_service.app.api.models.product import Product
from apps.product_service.app.api.schemas.product import ProductBase


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
