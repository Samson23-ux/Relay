from shared.utils import log_error
from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from apps.user_service.app.api.models.user import User
from apps.user_service.app.api.schemas.user import UserInDB
from apps.user_service.app.api.repo.user import UserRepository
from apps.user_service.app.core.exceptions import UserNotFoundError


class UserService:
    def __init__(self, user_repo: UserRepository, redis_repo: RedisRepository):
        self._user_repo = user_repo
        self._redis_repo = redis_repo

    async def get_user_by_email(
        self, circuit_key: str, request_meta: dict, **filters
    ) -> User:
        if "email" in filters:
            user_email: str = filters["email"]
        else:
            user_email: str = filters["google_email"]

        try:
            user: User | None = await self._user_repo.get_record(**filters)

            if not user:
                message = f"User not found with email {user_email}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise UserNotFoundError(user_email=user_email)

            return user
        except Exception as e:
            if isinstance(e, UserNotFoundError):
                raise UserNotFoundError(user_email=user_email) from e

            message = f"Error occured while retrieving user with email {user_email}. Error: {str(e)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    async def _get_user_by_email(self, **filters) -> User | None:
        return await self._user_repo.get_record(**filters)

    async def create_user(
        self, circuit_key: str, request_meta: dict, user: UserInDB, email: str
    ):
        try:
            self._user_repo.add(entity=user)
            await self._user_repo.commit()
        except Exception as e:
            await self._user_repo.rollback()

            message = (
                f"Error occured while creating user with email {email}. Error: {str(e)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    async def update_user(self, circuit_key: str, request_meta: dict, user: User):
        try:
            self._user_repo.add(model=user)
            await self._user_repo.commit()
            await self._user_repo.refresh(user)
        except Exception as e:
            await self._user_repo.rollback()

            message = f"Error occured while updating user with email {user.email}. Error: {str(e)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    async def delete_user(self, circuit_key: str, request_meta: dict, user: User):
        try:
            await self._user_repo.delete(user)
            await self._user_repo.commit()
        except Exception as e:
            await self._user_repo.rollback()

            message = f"Error occured while deleting user with email {user.email}. Error: {str(e)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e
