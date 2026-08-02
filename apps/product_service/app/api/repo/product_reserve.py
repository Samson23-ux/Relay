from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


from shared.repo.base_repo import BaseRepository
from apps.product_service.app.api.models.product_reserve import ProductReserve
from apps.product_service.app.api.schemas.product_reserve import ProductReserveBase


class ProductReserveRepository(BaseRepository[ProductReserveBase, ProductReserve]):
    model = ProductReserve

    def _entity_to_model(self, entity):
        return ProductReserve(**entity.model_dump())

    def _get_filters(self, **filters):
        filter_conditions = []

        if "order_id" in filters:
            filter_conditions.append(self.model.order_id == filters["order_id"])
        if "product_id" in filters:
            filter_conditions.append(self.model.product_id == filters["product_id"])
        return filter_conditions

    def _get_sort_fields(self, sort):
        return super()._get_sort_fields(sort)

    def reserve_product(self, entity: ProductReserveBase):
        insert_stmt = insert(self.model).values(entity.model_dump())

        update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["order_id", "product_id"],
            set_={"reserve": ProductReserve.reserve + insert_stmt.excluded.reserve},
        )

        self._sync_session.execute(update_stmt)

    def get_product_reserve(
        self, order_id: UUID, product_id: UUID
    ) -> ProductReserve | None:
        stmt = (
            select(self.model)
            .where(
                self.model.order_id == order_id,
                self.model.product_id == product_id,
            )
            .with_for_update()
        )

        res = self._sync_session.execute(stmt)
        return res.scalar()
