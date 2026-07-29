from shared.repo.redis import RedisRepository
from shared.worker.db import get_db_session, get_redis_client


def get_email_service():
    from apps.user_service.app.api.repo.email import EmailRepository
    from apps.user_service.app.api.services.email import EmailService

    redis = next(get_redis_client())
    session = next(get_db_session())

    email_service: EmailService = EmailService(
        redis_repo=RedisRepository(sync_redis=redis),
        email_repo=EmailRepository(sync_session=session)
    )

    return email_service


def get_user_service():
    from apps.user_service.app.api.repo.user import UserRepository
    from apps.user_service.app.api.services.user import UserService

    redis = next(get_redis_client())
    session = next(get_db_session())

    user_service: UserService = UserService(
        redis_repo=RedisRepository(sync_redis=redis),
        user_repo=UserRepository(sync_session=session)
    )
    return user_service


def get_otp_service():
    from apps.user_service.app.api.repo.otp import OtpRepository
    from apps.user_service.app.api.services.otp import OtpService

    session = next(get_db_session())
    otp_service: OtpService = OtpService(otp_repo=OtpRepository(sync_session=session))
    return otp_service
