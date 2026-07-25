from shared import get_db_session
from apps.user_service import (
    OtpRepository,
    OtpService,
    UserRepository,
    UserService,
    EmailRepository,
    EmailService,
)


def get_email_service() -> EmailService:
    session = get_db_session()

    email_service: EmailService = EmailService(
        email_repo=EmailRepository(sync_session=session)
    )

    return email_service


def get_user_service() -> UserService:
    session = get_db_session()
    user_service: UserService = UserService(
        user_repo=UserRepository(sync_session=session)
    )
    return user_service


def get_otp_service() -> OtpService:
    session = get_db_session()
    otp_service: OtpService = OtpService(otp_repo=OtpRepository(sync_session=session))
    return otp_service
