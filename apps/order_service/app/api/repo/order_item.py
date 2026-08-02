from shared.repo.base_repo import BaseRepository
from apps.order_service.app.api.models.order_item import OrderItem
from apps.order_service.app.api.schemas.order_item import OrderItemBase


class OrderItemRepository(BaseRepository[OrderItemBase, OrderItem]):
    model = OrderItem

    def _entity_to_model(self, entity):
        return OrderItem(entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "order_id" in filters:
            filter_conditions.append(self.model.order_id == filters["order_id"])
        if "product_id" in filters:
            filter_conditions.append(self.model.product_id == filters["product_id"])

    def _get_sort_fields(self, sort):
        return [self.model.created_at]
