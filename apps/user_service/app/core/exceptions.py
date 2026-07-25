from shared import AppException


class AuthenticationError(AppException):
    """User not authenticated."""

    pass


class AuthorizationError(AppException):
    """User not authorized"""

    pass


class UserExistsError(AppException):
    """User already exists"""

    def __init__(self, user_email: str):
        self.user_email = user_email


class UserNotFoundError(AppException):
    """User not found"""

    def __init__(self, user_email: str):
        self.user_email = user_email


class InvalidOtpError(AppException):
    """Invalid otp received"""

    pass


class CredentialError(AppException):
    """wrong credentials provided"""

    pass
