from uuid import UUID
from typing import Any
from sqlalchemy import select, desc, insert


from shared.repo.base_repo import BaseRepository
from apps.order_service.app.api.models.order import Order
from apps.product_service.app.api.models.product import Product
from apps.order_service.app.api.models.order_item import OrderItem
from apps.order_service.app.api.schemas.order_item import OrderItemBase


class OrderItemRepository(BaseRepository[OrderItemBase, OrderItem]):
    model = OrderItem

    def _entity_to_model(self, entity):
        return OrderItem(**entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "order_id" in filters:
            filter_conditions.append(self.model.order_id == filters["order_id"])
        if "product_id" in filters:
            filter_conditions.append(self.model.product_id == filters["product_id"])

        return filter_conditions

    def _get_sort_fields(self, sort):
        return [self.model.created_at]

    async def get_order_with_items(self, user_id: UUID, **filters):
        filter_conditions = self._get_filters(**filters)

        stmt = (
            select(
                Product.id,
                Product.name,
                Product.description,
                Product.serial,
                self.model.quantity,
                self.model.price,
                self.model.total_price,
                self.model.created_at,
                Order.id,
            )
            .select_from(Order)
            .join(self.model, Order.id == self.model.order_id)
            .join(Product, Product.id == self.model.product_id)
            .where(*filter_conditions, Order.user_id == user_id)
        )
        res = await self._async_session.execute(stmt)
        return res.all()

    async def get_orders_with_items(self, user_id: UUID, sort: str | None, order: str):
        stmt = (
            select(
                Product.id,
                Product.name,
                Product.description,
                Product.serial,
                self.model.quantity,
                self.model.price,
                self.model.total_price,
                self.model.created_at,
                Order.id,
            )
            .select_from(Order)
            .join(self.model, Order.id == self.model.order_id)
            .join(Product, Product.id == self.model.product_id)
            .where(Order.user_id == user_id)
        )

        if sort:
            sort_fields: list[Any] = self._get_sort_fields(sort)
            if order == "desc":
                stmt = stmt.order_by(desc(*sort_fields))
            else:
                stmt = stmt.order_by(*sort_fields)

        res = await self._async_session.execute(stmt)
        return res.all()

    async def get_orders_for_deletion(self, user_id: UUID, **filters):
        filter_conditions = self._get_filters(**filters)

        stmt = (
            select(
                Order.status,
                Product.id,
                self.model.quantity
            )
            .select_from(Order)
            .join(self.model, Order.id == self.model.order_id)
            .join(Product, Product.id == self.model.product_id)
            .where(*filter_conditions, Order.user_id == user_id)
        )
        res = await self._async_session.execute(stmt)
        return res.all()

    async def insert_order_items(self, order_items: list[dict]):
        await self._async_session.execute(insert(self.model).values(order_items))
