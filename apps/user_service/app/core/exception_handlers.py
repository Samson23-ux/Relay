from fastapi import FastAPI


from shared.schemas.response import ErrorResponse
from shared.core.exceptions import create_exception_handler
from apps.user_service.app.core.exceptions import (
    CredentialError,
    UserExistsError,
    InvalidOtpError,
    UserNotFoundError,
)


class UserExceptionHandler:
    def __init__(self, app: FastAPI):
        self._app = app

    def add_handlers(self):
        self._app.add_exception_handler(
            exc_class_or_status_code=UserExistsError,
            handler=create_exception_handler(
                status_code=409,
                initial_detail=ErrorResponse(
                    message="User already exists with the provided email {user_email}"
                ),
            ),
        )

        self._app.add_exception_handler(
            InvalidOtpError,
            create_exception_handler(
                status_code=400,
                initial_detail=ErrorResponse(message="Invalid otp received"),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=UserNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail=ErrorResponse(
                    message="User not found with email {user_email}"
                ),
            ),
        )

        self._app.add_exception_handler(
            CredentialError,
            create_exception_handler(
                status_code=400,
                initial_detail=ErrorResponse(message="Invalid credentials!"),
            ),
        )
