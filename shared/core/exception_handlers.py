from fastapi import FastAPI


from shared.core.exceptions import create_exception_handler
from shared.core.exceptions import ServerError, ServiceUnavailable


class GlobalExceptionHandler:
    def __init__(self, app: FastAPI):
        self._app = app

    def add_handlers(self):
        self._app.add_exception_handler(
            ServerError,
            create_exception_handler(
                status_code=500,
                initial_detail={
                    "status": "error",
                    "message": "Oops! Something went wrong.",
                },
            ),
        )

        self._app.add_exception_handler(
            ServiceUnavailable,
            create_exception_handler(
                status_code=503,
                initial_detail={
                    "status": "error",
                    "message": "Service unavailble! Try again after five minutes",
                },
            ),
        )
