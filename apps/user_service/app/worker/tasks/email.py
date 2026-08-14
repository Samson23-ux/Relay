import secrets
import psycopg2
from uuid import UUID
from celery.exceptions import Reject
from resend.exceptions import ResendError
from datetime import datetime, timezone, timedelta


from shared.worker.celery_app import celery_app
from shared.worker.services import get_redis_repo
from shared.core.exceptions import MaxRetriesError
from shared.worker.tasks.base import BaseTaskWithFailure
from apps.user_service.app.api.models.email import Email
from shared.core.shared_config import get_global_settings
from apps.user_service.app.api.schemas.auth import OtpInDB
from apps.user_service.app.core.config import get_user_settings
from apps.user_service.app.worker.services import get_otp_service

USER_SETTINGS = get_user_settings()
GLOBAL_SETTINGS = get_global_settings()

SENDER_EMAIL = GLOBAL_SETTINGS.API_EMAIL
RESEND_API_KEY = GLOBAL_SETTINGS.RESEND_API_KEY


def verification_message(otp: str):
    return f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                </head>
                <body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,sans-serif;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
                    <tr>
                        <td align="center">
                        <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
                            <tr>
                            <td align="center" style="padding-bottom:24px;">
                                <h2 style="margin:0;color:#1a1a1a;font-size:22px;">Verify your email</h2>
                            </td>
                            </tr>
                            <tr>
                            <td align="center" style="padding-bottom:16px;">
                                <p style="margin:0;color:#555555;font-size:15px;line-height:1.6;">
                                Use the code below to complete your verification. It expires in <strong>15 minutes</strong>.
                                </p>
                            </td>
                            </tr>
                            <tr>
                            <td align="center" style="padding:24px 0;">
                                <div style="display:inline-block;background:#f0f4ff;border-radius:8px;padding:16px 40px;">
                                <span style="font-size:36px;font-weight:bold;letter-spacing:10px;color:#3b5bdb;">{otp}</span>
                                </div>
                            </td>
                            </tr>
                            <tr>
                            <td align="center" style="padding-top:16px;">
                                <p style="margin:0;color:#999999;font-size:13px;">
                                If you did not request this, please ignore this email.
                                </p>
                            </td>
                            </tr>
                        </table>
                        </td>
                    </tr>
                    </table>
                </body>
            </html>
            """


@celery_app.task(base=BaseTaskWithFailure, bind=True)
def send_verification_email(
    self,
    circuit_key: str,
    request_meta: dict,
    email_id: str,
    recipient_email: str,
    user_id: str,
):
    from apps.user_service.app.worker.services import get_email_service

    try:
        user_id: UUID = UUID(user_id)
        email_id: UUID = UUID(email_id)

        redis_repo = get_redis_repo()
        otp_service = get_otp_service()
        email_service = get_email_service()

        key: str = f"idempotency:{email_id}"
        already_processed: str | None = redis_repo.sync_get_key(key)

        if not already_processed:
            otp: str = str(secrets.randbelow(900000) + 100000)

            email_service.api_key = RESEND_API_KEY
            email_service.send(
                SENDER_EMAIL,
                recipient_email,
                "Email Verification Code",
                verification_message(otp),
            )

            redis_repo.mark_task_processed(
                key, "1", GLOBAL_SETTINGS.IDEMPOTENCY_KEY_TTL
            )

            email: Email = email_service.get_processed_email(email_id)
            email.status = "delivered"
            email.delivered_at = datetime.now(timezone.utc)
            email_service.update_processed_email(circuit_key, request_meta, email)

            otp_payload: OtpInDB = OtpInDB(
                otp=otp,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=USER_SETTINGS.OTP_EXPIRE_TIME),
            )

            otp_service.create_otp(otp_payload)
    except (
        ResendError,
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
        psycopg2.extensions.TransactionRollbackError,
    ) as exc:
        """retry for transient errors"""
        try:
            if isinstance(exc, ResendError):
                if hasattr(exc, "code") and exc.code >= 500:
                    raise self.retry(
                        exc=MaxRetriesError(str(exc)),
                        countdown=self._backoff_countdown(),
                    )
            raise self.retry(
                exc=MaxRetriesError(str(exc)), countdown=self._backoff_countdown()
            )
        except MaxRetriesError as exc:
            self._handle_failure(self.request.kwargs)
            raise Reject(exc, requeue=False)
    except Exception as exc:
        self._handle_failure(self.request.kwargs)
        raise Reject(exc, requeue=False)
