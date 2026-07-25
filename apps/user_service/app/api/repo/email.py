from typing import Any


from shared.repo.base_repo import BaseRepository
from apps.user_service.app.api.models.email import Email
from apps.user_service.app.api.schemas.email import EmailBase


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
