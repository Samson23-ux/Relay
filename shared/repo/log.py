from shared.models.log import Log
from shared.schemas.log import LogBase
from shared.repo.base_repo import BaseRepository


class LogRepository(BaseRepository[LogBase, Log]):
    model = Log

    def _entity_to_model(self, entity):
        return Log(**entity.model_dump())
    
    def _get_filters(self, **filters):
        filter_conditions = []

        if "trace_id" in filters:
            filter_conditions.append(self.model.trace_id == filters["trace_id"])
        if "span_id" in filters:
            if filters["span_id"] is None:
                filter_conditions.append(self.model.span_id.is_(filters["span_id"]))
            else:
                filter_conditions.append(self.model.span_id == filters["span_id"])
        if "upstream" in filters:
            filter_conditions.append(self.model.upstream == filters["upstream"])

    def _get_sort_fields(self, sort):
        return super()._get_sort_fields(sort)
