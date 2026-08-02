from sqlalchemy import select


from shared.repo.base_repo import BaseRepository
from apps.order_service.app.api.models.cart import Cart
from apps.order_service.app.api.schemas.cart import CartBase


class CartRepository(BaseRepository[CartBase, Cart]):
    model = Cart

    def _entity_to_model(self, entity):
        return Cart(**entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "id" in filters:
            filter_conditions.append(self.model.id == filters["id"])
        if "user_id" in filters:
            filter_conditions.append(self.model.user_id == filters["user_id"])
        return filter_conditions

    def _get_sort_fields(self, sort):
        return super()._get_sort_fields(sort)

    async def get_cart_with_lock(self, read: bool, **filters) -> Cart | None:
        filter_conditions = self._get_filters(**filters)

        base_stmt = select(self.model).where(*filter_conditions)

        if read:
            base_stmt = base_stmt.with_for_update(read=True)
        else:
            base_stmt = base_stmt.with_for_update()

        res = await self._async_session.execute(base_stmt)
        return res.scalar()
