from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


from shared.schemas.response import ErrorResponse


class AppException(Exception):
    pass


class ServerError(AppException):
    """Internal Server error."""

    pass


class ServiceUnavailable(AppException):
    """Service unavailable temporarily"""

    pass


class MaxRetriesError(AppException):
    """Maximum retries exceeded"""

    pass


def create_exception_handler(
    status_code: int, initial_detail: ErrorResponse
) -> callable[[Request, AppException], JSONResponse]:
    async def exception_handler(request: Request, exc: AppException):
        initial_detail_dict: dict = initial_detail.model_dump()
        message: str = initial_detail_dict.get("message")
        initial_detail_dict["message"] = message.format(**exc.__dict__)

        return JSONResponse(content=initial_detail_dict, status_code=status_code)

    return exception_handler
