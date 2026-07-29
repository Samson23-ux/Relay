import resend
from uuid import UUID

from shared.utils import log_error
from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from apps.user_service.app.api.models.email import Email
from apps.user_service.app.api.schemas.email import EmailInDB
from apps.user_service.app.api.repo.email import EmailRepository


class EmailService:
    def __init__(self, email_repo: EmailRepository, redis_repo: RedisRepository):
        self._api_key = None
        self._redis_repo = redis_repo
        self._email_repo = email_repo

    async def create_email(
        self, circuit_key: str, request_meta: dict, email_payload: EmailInDB
    ):
        try:
            self._email_repo.add(entity=email_payload)
            await self._email_repo.commit()
        except Exception as e:
            await self._email_repo.rollback()

            message = f"Error occured while creating email record. Error: {str(e)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    def get_processed_email(self, email_id: UUID) -> Email | None:
        email: Email | None = self._email_repo.get_sync_record(id=email_id)
        return email

    def update_processed_email(self, circuit_key: str, request_meta: dict, email: Email):
        try:
            self._email_repo.sync_add(model=email)
            self._email_repo.sync_commit()
        except Exception as e:
            self._email_repo.sync_rollback()

            message = f"Error occured while updating email record. Error: {str(e)}"
            circuit: dict = self._redis_repo.sync_get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, api_key: str):
        self._api_key = api_key
        resend.api_key = self._api_key

    def send(self, sender: str, recipient: str, subject: str, body: str):
        resend.Emails.send(
            {
                "from": sender,
                "to": recipient,
                "subject": subject,
                "html": body,
            }
        )
