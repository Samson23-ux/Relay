import sentry_sdk
from uuid import UUID


from shared.models.log import Log
from shared.schemas.log import LogCreate
from shared.repo.log import LogRepository
from shared.core.exceptions import ServerError


class LogService:
    def __init__(self, log_repo: LogRepository):
        self._log_repo = log_repo

    def get_log(self, trace_id: UUID, span_id: UUID | None) -> Log | None:
        return self._log_repo.get_record(trace_id=trace_id, span_id=span_id)

    def create_log(self, log_create: LogCreate):
        try:
            self._log_repo.sync_add(entity=log_create)
            self._log_repo.sync_commit()
        except Exception as exc:
            self._log_repo.sync_rollback()
            sentry_sdk.capture_exception(exc)
            raise ServerError()

    def update_log(self, log: Log):
        try:
            self._log_repo.sync_add(model=log)
            self._log_repo.sync_commit()
        except Exception as exc:
            self._log_repo.sync_rollback()
            sentry_sdk.capture_exception(exc)
            raise ServerError()
