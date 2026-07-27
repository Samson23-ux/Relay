from shared.worker.db import get_db_session
from apps.user_service.app.api.repo.otp import OtpRepository
from apps.user_service.app.api.services.otp import OtpService
from apps.user_service.app.api.repo.user import UserRepository
from apps.user_service.app.api.services.user import UserService
from apps.user_service.app.api.repo.email import EmailRepository
from apps.user_service.app.api.services.email import EmailService


def get_email_service() -> EmailService:
    session = next(get_db_session())

    email_service: EmailService = EmailService(
        email_repo=EmailRepository(sync_session=session)
    )

    return email_service


def get_user_service() -> UserService:
    session = next(get_db_session())
    user_service: UserService = UserService(
        user_repo=UserRepository(sync_session=session)
    )
    return user_service


def get_otp_service() -> OtpService:
    session = next(get_db_session())
    otp_service: OtpService = OtpService(otp_repo=OtpRepository(sync_session=session))
    return otp_service
