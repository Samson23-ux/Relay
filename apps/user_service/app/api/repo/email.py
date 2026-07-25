from typing import Any


from shared import BaseRepository
from apps.user_service import Email, EmailBase


class EmailRepository(BaseRepository[EmailBase, Email]):
    model = Email

    @staticmethod
    def _entity_to_model(entity: EmailBase) -> Email:
        return Email(**entity.model_dump())

    def _get_filters(self, **filters) -> list[Any]:
        filter_conditions = []

        if "id" in filters:
            filter_conditions.append(self.model.id == filters["id"])
        return filter_conditions
