from shared import RedisRepository
from apps.user_service import OtpRepository


class AuthService:
    def __init__(self, otp_repo: OtpRepository, redis_repo: RedisRepository):
        self._uow = None
        self._user_repo = None
        self._otp_repo = otp_repo
        self._redis_repo = redis_repo
