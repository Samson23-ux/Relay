from sqlalchemy import insert, delete


from shared.repo.base_repo import BaseRepository
from apps.order_service.app.api.models.order import Order
from apps.order_service.app.api.schemas.order import OrderBase, OrderInDB


class OrderRepository(BaseRepository[OrderBase, Order]):
    model = Order

    def _entity_to_model(self, entity):
        return Order(**entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "id" in filters:
            filter_conditions.append(self.model.id == filters["id"])
        if "user_id" in filters:
            filter_conditions.append(self.model.user_id == filters["user_id"])

        return filter_conditions

    def _get_sort_fields(self, sort):
        return [self.model.created_at]

    async def insert_order(self, entity: OrderInDB):
        stmt = insert(self.model).values(**entity.model_dump())
        await self._async_session.execute(stmt)

    async def delete_order(self, order_id: str):
        stmt = delete(self.model).where(self.model.id == order_id)
        await self._async_session.execute(stmt)
