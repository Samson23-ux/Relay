from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


from shared.repo.base_repo import BaseRepository
from apps.order_service.app.api.models.cart import Cart
from apps.product_service.app.api.models.product import Product
from apps.order_service.app.api.models.cart_item import CartItem
from apps.order_service.app.api.schemas.cart_item import CartItemBase, CartItemInDB


class CartItemRepository(BaseRepository[CartItemBase, CartItem]):
    model = CartItem

    def _entity_to_model(self, entity):
        return CartItem(**entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "cart_id" in filters:
            filter_conditions.append(self.model.cart_id == filters["cart_id"])
        if "product_id" in filters:
            filter_conditions.append(self.model.product_id == filters["product_id"])
        return filter_conditions

    def _get_sort_fields(self, sort):
        return super()._get_sort_fields(sort)

    async def get_cart_item(self, **filters) -> CartItem | None:
        filter_conditions = self._get_filters(**filters)

        stmt = select(self.model).where(*filter_conditions).with_for_update()
        res = await self._async_session.execute(stmt)
        return res.scalar()

    async def get_cart_with_items(self, user_id: UUID, **filters):
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
            )
            .select_from(Cart)
            .join(self.model, Cart.id == self.model.cart_id)
            .join(Product, Product.id == self.model.product_id)
            .where(*filter_conditions, Cart.user_id == user_id)
        )
        res = await self._async_session.execute(stmt)
        return res.all()

    async def get_carts_with_items(self, user_id: UUID):
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
            )
            .select_from(Cart)
            .join(self.model, Cart.id == self.model.cart_id)
            .join(Product, Product.id == self.model.product_id)
            .where(Cart.user_id == user_id)
        )
        res = await self._async_session.execute(stmt)
        return res.all()

    async def insert_cart_item(self, entity: CartItemInDB):
        insert_stmt = insert(self.model).values(entity.model_dump())
        update_stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=["cart_id", "product_id"]
        )
        await self._async_session.execute(update_stmt)
