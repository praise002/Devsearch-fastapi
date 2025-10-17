from typing import Any, Callable

from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse


def register_all_errors(app: FastAPI):
    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "status": "failure",
                "message": "User with email already exists.",
                "err_code": "user_exists",
            },
        ),
    )
    
    app.add_exception_handler(
        UsernameAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "status": "failure",
                "message": "User with username already exists.",
                "err_code": "username_exists",
            },
        ),
    )

    app.add_exception_handler(
        UserNotFound,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "status": "failure",
                "message": "User not found.",
                "err_code": "user_not_found",
            },
        ),
    )

    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "status": "failure",
                "message": "Invalid email or password.",
                "error_code": "invalid_email_or_password",
            },
        ),
    )

    app.add_exception_handler(
        InvalidOtp,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "status": "failure",
                "message": "Invalid otp or otp expired.",
                "resolution": "Please get a new otp",
                "error_code": "invalid_otp",
            },
        ),
    )

    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Invalid token or token expired.",
                "resolution": "Please get a new token",
                "error_code": "invalid_token",
            },
        ),
    )

    app.add_exception_handler(
        GoogleAuthenticationFailed,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Google authentication failed.",
                "resolution": "Please get a new token",
                "error_code": "google_auth_failed",
            },
        ),
    )

    app.add_exception_handler(
        RevokedToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Token is invalid or has been revoked.",
                "resolution": "Please get a new token",
                "error_code": "token_revoked",
            },
        ),
    )

    app.add_exception_handler(
        AccessTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Please provide a valid access token.",
                "resolution": "Please get an access token",
                "error_code": "access_token_required",
            },
        ),
    )

    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Please provide a valid refresh token.",
                "resolution": "Please get a refresh token",
                "error_code": "refresh_token_required",
            },
        ),
    )

    app.add_exception_handler(
        InsufficientPermission,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "status": "failure",
                "message": "You do not have sufficient permissions to perform this action.",
                "resolution": "Please check your permissions or contact an administrator.",
                "error_code": "insufficient_permission",
            },
        ),
    )

    app.add_exception_handler(
        AccountNotVerified,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "status": "failure",
                "message": "Account not verified.",
                "resolution": "Please check your email for verification details.",
                "error_code": "account_not_verified",
            },
        ),
    )

    app.add_exception_handler(
        UserNotActive,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "status": "failure",
                "message": "Your account has been disabled. Please contact support for assistance",
                "error_code": "forbidden",
            },
        ),
    )

    app.add_exception_handler(
        PasswordMismatch,
        create_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            initial_detail={
                "status": "failure",
                "message": "New password and confirm password do not match.",
                "error_code": "password_mismatch",
            },
        ),
    )

    app.add_exception_handler(
        InvalidOldPassword,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "status": "failure",
                "message": "Invalid old password.",
                "error_code": "invalid_old_password",
            },
        ),
    )

    @app.exception_handler(500)
    async def internal_server_error(request, exc):
        return JSONResponse(
            content={
                "status": "failure",
                "message": "Ooops! Something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BaseException(Exception):
    """This is the base class for all Base errors"""

    pass


class InvalidOtp(BaseException):
    """User has provided an invalid or expired otp"""

    pass


class InvalidToken(BaseException):
    """User has provided an invalid or expired token"""

    pass


class RevokedToken(BaseException):
    """User has provided a token that has been revoked"""

    pass


class AccessTokenRequired(BaseException):
    """User has provided a refresh token when an access token is needed"""

    pass


class RefreshTokenRequired(BaseException):
    """User has provided an access token when a refresh token is needed"""

    pass


class UserAlreadyExists(BaseException):
    """User has provided an email for a user who exists during sign up"""

    pass

class UsernameAlreadyExists(BaseException):
    """Username exists"""

    pass


class InvalidCredentials(BaseException):
    """User has provided wrong email or password during login"""

    pass


class InsufficientPermission(BaseException):
    """User does not have the neccessary permissions to perform an action"""

    pass


class UserNotFound(BaseException):
    """User not found"""

    pass


class AccountNotVerified(BaseException):
    """Account not yet verified"""

    pass


class UserNotActive(BaseException):
    """User not active"""

    pass


class PasswordMismatch(BaseException):
    """New password and confirm password deosn't match"""

    pass


class InvalidOldPassword(BaseException):
    """Invalid old password"""

    pass


class GoogleAuthenticationFailed(BaseException):
    """Google authentication failed"""

    pass


def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:
    async def exception_handler(request: Request, exc: BaseException):
        return JSONResponse(content=initial_detail, status_code=status_code)
    
    return exception_handler
