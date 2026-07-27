from shared.repo.log import LogRepository


class LogService:
    def __init__(self, log_repo: LogRepository):
        self._log_repo = log_repo
