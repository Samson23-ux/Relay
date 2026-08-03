from shared.repo.base_repo import BaseRepository
from apps.order_service.app.api.models.order import Order
from apps.order_service.app.api.schemas.order import OrderBase


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
