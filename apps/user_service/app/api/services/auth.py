from uuid import UUID, uuid4


from shared.utils import log_error, log_info
from shared.repo.redis import RedisRepository
from shared.core.exceptions import ServerError
from shared.repo.uow import UnitOfWorkRepository
from apps.user_service.app.api.models.otp import Otp
from apps.user_service.app.utils import get_user_email
from apps.user_service.app.api.models.user import User
from apps.user_service.app.core.security import Security
from apps.user_service.app.api.repo.otp import OtpRepository
from apps.user_service.app.api.schemas.email import EmailInDB
from apps.user_service.app.api.repo.user import UserRepository
from apps.user_service.app.core.config import get_user_settings
from apps.user_service.app.api.services.user import UserService
from apps.user_service.app.api.services.email import EmailService
from apps.user_service.app.worker.tasks.email import send_verification_email
from apps.user_service.app.api.schemas.auth import (
    TokenData,
    ResendOtp,
    EmailLogin,
    EmailVerify,
)
from apps.user_service.app.core.exceptions import (
    CredentialError,
    UserExistsError,
    InvalidOtpError,
)
from apps.user_service.app.api.schemas.user import (
    UserInDB,
    EmailUserResponse,
    GoogleUserResponse,
)


class AuthService:
    def __init__(self, otp_repo: OtpRepository, redis_repo: RedisRepository):
        self._uow = None
        self._user_repo = None
        self._otp_repo = otp_repo
        self._redis_repo = redis_repo

    SETTINGS = get_user_settings()

    async def _get_tokens(
        self,
        role: str,
        email: str,
        user_type: str,
        circuit_key: str,
        request_meta: dict,
        security: Security,
    ):
        token_data: TokenData = TokenData(email=email, role=role, user_type=user_type)
        access_token, refresh_token_payload = await security.prepare_tokens(token_data)

        refresh_token_id: str = refresh_token_payload.get("refresh_token_id")
        key: str = f"tokens:{refresh_token_id}"

        try:
            await self._redis_repo.create_hset(key, refresh_token_payload)
            return access_token, refresh_token_payload.get("refresh_token")
        except Exception as e:
            message = (
                f"Error occurred while saving refresh token to redis. Error: {str(e)}"
            )
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    async def sign_up_with_email(
        self,
        request_meta: dict,
        email_login: EmailLogin,
        user_service: UserService,
        email_service: EmailService,
        security: Security,
    ):
        email_id: str = str(uuid4())
        user_email: str = email_login.email
        hashed_password: str = await security.hash_password(email_login.password)

        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        existing_user: User | None = await user_service._get_user_by_email(
            email=user_email
        )

        if existing_user:
            if not existing_user.is_verified:
                existing_user.hashed_password = hashed_password
                await user_service.update_user(circuit_key, request_meta, existing_user)

                email_db: EmailInDB = EmailInDB(
                    id=email_id, processed_email=existing_user.email
                )
                await email_service.create_email(circuit_key, request_meta, email_db)

                send_verification_email.apply_async(
                    priority=5,
                    kwargs={
                        "circuit_key": circuit_key,
                        "request_meta": request_meta,
                        "email_id": email_id,
                        "recipient_email": existing_user.email,
                        "user_id": str(existing_user.id),
                    },
                )
            else:
                message = f"User exists with email {user_email}"
                circuit: dict = await self._redis_repo.get_hset(circuit_key)

                log_error(message, request_meta, circuit)
                raise UserExistsError(user_email=user_email)
        else:
            user = UserInDB(
                email=user_email, hashed_password=hashed_password, type="email"
            )
            await user_service.create_user(circuit_key, request_meta, user, user_email)

            user: User | None = await user_service._get_user_by_email(email=user_email)

            email_db: EmailInDB = EmailInDB(id=email_id, processed_email=user_email)
            await email_service.create_email(circuit_key, request_meta, email_db)

            send_verification_email.apply_async(
                priority=5,
                kwargs={
                    "circuit_key": circuit_key,
                    "request_meta": request_meta,
                    "email_id": email_id,
                    "recipient_email": user_email,
                    "user_id": str(user.id),
                },
            )
        message = f"Email and password sign up completed for user {user_email}"
        circuit: dict = await self._redis_repo.get_hset(circuit_key)

        log_info(message, request_meta, circuit)

    async def sign_up_with_google(
        self,
        request_meta: dict,
        payload: dict,
        user_service: UserService,
        security: Security,
    ) -> tuple[str]:
        user_info: dict = payload.get("userinfo")
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        google_id: str = user_info.get("sub")
        user_email: str = user_info.get("email")

        existing_user: User | None = await user_service._get_user_by_email(
            google_email=user_email,
            is_verified=True,
        )

        if existing_user:
            existing_user.is_active = True
            await user_service.update_user(circuit_key, request_meta, existing_user)
        else:
            user = UserInDB(
                type="google",
                is_active=True,
                is_verified=True,
                google_id=google_id,
                google_email=user_email,
            )
            await user_service.create_user(circuit_key, request_meta, user, user_email)

        role: str = existing_user.role if existing_user else user.role
        access_token, refresh_token = await self._get_tokens(
            role, user_email, "google", circuit_key, request_meta, security
        )

        message = f"Google sign in completed for user {user_email}"
        circuit: dict = await self._redis_repo.get_hset(circuit_key)

        log_info(message, request_meta, circuit)
        return access_token, refresh_token

    async def verify_account(
        self,
        request_meta: dict,
        uow: UnitOfWorkRepository,
        email_verify: EmailVerify,
    ):
        # close active sessions
        await self._otp_repo.aclose()

        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        self._uow = uow
        self._user_repo = UserRepository(self._uow.session)
        self._otp_repo.async_session = self._uow.session

        user_email: str = email_verify.email

        existing_user: User | None = await self._user_repo.get_record(email=user_email)

        if not existing_user:
            message = f"User not found with email {user_email}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise InvalidOtpError()

        otp: Otp = await self._otp_repo.get_record(
            otp=email_verify.otp_code,
            user_id=existing_user.id,
            status="valid",
            expires_at=True,
        )

        if not otp:
            message = f"Invalid otp received from user {user_email}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise InvalidOtpError()

        try:
            existing_user.is_verified = True

            otp.status = "used"
            self._otp_repo.add(model=otp)
            self._user_repo.add(model=existing_user)

            await self._uow.commit()

            message = f"User {user_email} account verification completed"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
        except Exception as e:
            await self._uow.rollback()

            message = f"Error occured while trying to verify user {user_email} account. Error: {str(e)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    async def resend_otp(
        self,
        request_meta: dict,
        otp_resend: ResendOtp,
        user_service: UserService,
        email_service: EmailService,
    ):
        user_email: str = otp_resend.email
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        existing_user: User | None = await user_service._get_user_by_email(
            email=user_email, is_verified=False
        )

        if not existing_user:
            message = f"User with email {user_email} not found"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise CredentialError()

        try:
            # invalidate all existing codes
            await self._otp_repo.update_records(
                {"status": "used"}, user_id=existing_user.id, status="valid"
            )

            email_id: str = str(uuid4())
            email_db: EmailInDB = EmailInDB(
                id=email_id, processed_email=existing_user.email
            )
            await email_service.create_email(circuit_key, request_meta, email_db)

            send_verification_email.apply_async(
                priority=5,
                kwargs={
                    "circuit_key": circuit_key,
                    "request_meta": request_meta,
                    "email_id": email_id,
                    "recipient_email": user_email,
                    "user_id": str(existing_user.id),
                },
            )

            message = f"OTP code resent to user {user_email}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_info(message, request_meta, circuit)
        except Exception as e:
            await self._otp_repo.rollback()

            message = f"Error occured while resending otp to user {user_email}. Error: {str(e)}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise ServerError() from e

    async def login(
        self,
        request_meta: dict,
        email_login: EmailLogin,
        user_service: UserService,
        security: Security,
    ):
        user_email: str = email_login.email
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        existing_user: User | None = await user_service._get_user_by_email(
            email=user_email, is_verified=True, is_deactivated=False
        )

        if not existing_user:
            message = f"Invalid credentials received from user {user_email}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise CredentialError()

        if not await security.verify_password(
            email_login.password, existing_user.hashed_password
        ):
            message = f"Invalid credentials received from user {user_email}"
            circuit: dict = await self._redis_repo.get_hset(circuit_key)

            log_error(message, request_meta, circuit)
            raise CredentialError()

        existing_user.is_active = True
        await user_service.update_user(circuit_key, request_meta, existing_user)

        access_token, refresh_token = await self._get_tokens(
            existing_user.role, user_email, "email", circuit_key, request_meta, security
        )

        message = f"Login completed for user {user_email}"
        circuit: dict = await self._redis_repo.get_hset(circuit_key)

        log_info(message, request_meta, circuit)
        return access_token, refresh_token

    async def create_auth_tokens(
        self, curr_user: User, request_meta: dict, security: Security
    ):
        user_type: str = curr_user.type
        user_email: str = get_user_email(curr_user)

        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"
        access_token, refresh_token = await self._get_tokens(
            curr_user.role, user_email, user_type, circuit_key, request_meta, security
        )

        message = f"Access and refresh tokens created for user {user_email}"
        circuit: dict = await self._redis_repo.get_hset(circuit_key)

        log_info(message, request_meta, circuit)
        return access_token, refresh_token

    async def get_current_user(
        self, request_meta: dict, curr_user: User
    ) -> EmailUserResponse | GoogleUserResponse:
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        if curr_user.type == "email":
            user_email: str = curr_user.email
            user = EmailUserResponse.model_validate(curr_user)
        else:
            user_email: str = curr_user.google_email
            user = GoogleUserResponse.model_validate(curr_user)

        request_meta["user_id"] = curr_user.id
        message = f"User {user_email} account retrieved"

        circuit: dict = await self._redis_repo.get_hset(circuit_key)
        log_info(message, request_meta, circuit)

        return user

    async def logout(
        self,
        request_meta: dict,
        curr_user: User,
        user_service: UserService,
    ):
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        request_meta["user_id"] = curr_user.id
        user_email: str = get_user_email(curr_user)

        curr_user.is_active = False
        await user_service.update_user(circuit_key, request_meta, curr_user)

        message = f"User {user_email} account logout completed"
        circuit: dict = await self._redis_repo.get_hset(circuit_key)

        log_info(message, request_meta, circuit)

    async def delete_account(
        self,
        request_meta: dict,
        curr_user: User,
        user_service: UserService,
    ):
        user_email: str = get_user_email(curr_user)
        circuit_key: str = f"circuit:{request_meta.get("upstream_instance")}"

        request_meta["user_id"] = curr_user.id
        await user_service.delete_user(circuit_key, request_meta, curr_user)

        message = f"User {user_email} account deleted"
        circuit: dict = await self._redis_repo.get_hset(circuit_key)

        log_info(message, request_meta, circuit)
