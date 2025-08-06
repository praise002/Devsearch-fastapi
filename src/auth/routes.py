from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import (
    AccessTokenBearer,
    RefreshTokenBearer,
    RoleChecker,
    get_current_user,
)
from src.auth.schemas import (
    OtpVerify,
    PasswordChangeModel,
    PasswordResetConfirmModel,
    PasswordResetModel,
    PasswordResetVerifyOtpModel,
    SendOtp,
    UserCreate,
    UserLoginModel,
    UserResponse,
)
from src.auth.service import UserService
from src.auth.utils import (
    ACCESS_TOKEN_EXAMPLE,
    REFRESH_TOKEN_EXAMPLE,
    create_access_token,
    generate_otp,
    hash_password,
    invalidate_previous_otps,
    verify_password,
)
from src.config import Config
from src.db.main import get_session
from src.db.models import Profile, User
from src.db.redis import add_jti_to_blocklist
from src.errors import InvalidOtp, InvalidToken, UserNotFound
from src.mail import send_email

router = APIRouter()

user_service = UserService()
role_checker = RoleChecker(["admin", "user"])
REFRESH_TOKEN = Config.REFRESH_TOKEN_EXPIRY


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    description="This endpoint registers new users into our application",
)
async def create_user_account(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    email = user_data.email
    user_exists = await user_service.user_exists(email, session)
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User with email already exists.",
        )

    username = user_data.username
    username_exists = await user_service.username_exists(username, session)
    if username_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User with username already exists.",
        )

    hashed_password = hash_password(user_data.password)
    extra_data = {
        "hashed_password": hashed_password,
    }
    new_user = User.model_validate(user_data, update=extra_data)

    session.add(new_user)

    session.commit()
    session.refresh(new_user)

    profile = Profile(user_id=new_user.id)
    session.add(profile)
    session.commit()
    session.refresh(profile)

    otp = generate_otp(new_user, session)
    send_email(
        background_tasks,
        "Verify your email",
        new_user.email,
        {"name": new_user.first_name, "otp": str(otp)},
        "verify_email_request.html",
    )

    return {
        "message": "Account Created! Check email to verify your account",
        "email": new_user.email,
    }


@router.post(
    "/verification/verify",
    status_code=status.HTTP_200_OK,
    description="This endpoint verifies a user's email",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Email verified successfully",
                    }
                }
            },
        }
    },
)
async def verify_user_account(
    data: OtpVerify,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):

    email = data.email
    otp = data.otp

    user = await user_service.get_user_by_email(email, session)

    if not user:
        raise UserNotFound()

    otp_record = await user_service.get_otp_by_user(user_id, otp, session)
    user_id = user.id

    if not otp_record or not otp_record.is_valid:
        raise InvalidOtp()

    if user.is_email_verified:
        return {
            "message": "Email address already verified. No OTP sent",
        }

    user_service.update_user(user, {"is_email_verified": True}, session)

    invalidate_previous_otps(user, session)

    send_email(
        background_tasks,
        "Verify your email",
        user.email,
        {"name": user.first_name},
        "welcome_message",
    )

    return {
        "message": "Email verified successfully",
    }


@router.post(
    "/verification",
    status_code=status.HTTP_200_OK,
    description="This endpoint sends OTP to a user's email for verification",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "OtpResent": {
                            "summary": "OTP Resent Successful",
                            "value": {
                                "status": "success",
                                "message": "OTP sent successfully",
                            },
                        },
                        "EmailVerified": {
                            "summary": "Email already verified",
                            "value": {
                                "status": "success",
                                "message": "Email address already verified. No OTP sent",
                            },
                        },
                    }
                }
            },
        }
    },
)
async def resend_verification_email(
    data: SendOtp,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    email = data.email
    user = await user_service.get_user_by_email(email, session)

    if not user:
        raise UserNotFound()

    if user.is_email_verified:
        return {
            "status": "success",
            "message": "Email address already verified. No OTP sent",
        }

    invalidate_previous_otps(user, session)

    send_email(
        background_tasks,
        "Verify your email",
        user.email,
        {"name": user.first_name},
        "welcome_message",
    )

    return {
        "status": "success",
        "message": "OTP sent successfully",
    }


@router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    description="This endpoint generates new access and refresh tokens for authentication",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Login successful",
                        "access_token": ACCESS_TOKEN_EXAMPLE,
                        "refresh_token": REFRESH_TOKEN_EXAMPLE,
                    }
                }
            },
        },
        401: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "message": "No active account found with the given credentials",
                        "error_code": "unauthorized",
                    }
                }
            },
        },
        403: {
            "content": {
                "application/json": {
                    "examples": {
                        "EmailNotVerified": {
                            "summary": "Email not verified",
                            "value": {
                                "status": "failure",
                                "message": "Email not verified. Please verify your email before logging in",
                                "error_code": "forbidden",
                            },
                        },
                        "AccountDisabled": {
                            "summary": "Account disabled",
                            "value": {
                                "status": "failure",
                                "message": "Your account has been disabled. Please contact support for assistance",
                                "error_code": "forbidden",
                            },
                        },
                    }
                }
            },
        },
    },
)
async def login_user(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    email = login_data.email
    password = login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user is None or not verify_password(password, user.password_hash):
        return JSONResponse(
            content={
                "status": "failure",
                "message": "No active account found with the given credentials",
                "error_code": "unauthorized",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_email_verified:
        return JSONResponse(
            content={
                "status": "failure",
                "message": "Email not verified. Please verify your email before logging in",
                "error_code": "forbidden",
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if not user.is_active:
        return JSONResponse(
            content={
                "status": "failure",
                "message": "Your account has been disabled. Please contact support for assistance",
                "error_code": "forbidden",
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    password_valid = verify_password(password, user.password_hash)
    if password_valid:
        access_token = create_access_token(
            user_data={
                "email": user.email,
                "user_id": str(user.id),
                "role": user.role,
            }
        )
        refresh_token = create_access_token(
            user_data={
                "email": user.email,
                "user_id": str(user.id),
            },
            refresh=True,
            expiry=timedelta(days=90),
        )
        return {
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
        }  # TODO: USE HTTP-COOKIE LATER


@router.post(
    "/token/refresh",
    status_code=status.HTTP_200_OK,
    description="This endpoint allows users to refresh their access token using a valid refresh token. It returns a new access and refresh token, which can be used for further authenticated requests.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Token refreshed successfully",
                        "access_token": ACCESS_TOKEN_EXAMPLE,
                        "refresh_token": REFRESH_TOKEN_EXAMPLE,
                    }
                }
            },
        },
        401: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "message": "Invalid token or token expired.",
                        "resolution": "Please get a new token",
                        "error_code": "invalid_token",
                    }
                }
            }
        },
    },
)
async def refresh_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(user_data=token_details["user"])
        new_refresh_token = create_access_token(
            token_details["user"],
            refresh=True,
            expiry=timedelta(days=90),
        )
        return {
            "message": "Token refreshed successfully",
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }

    raise InvalidToken()


# TODO: PUT THE RESPONSE MODEL LATER
# TODO: CONTINUE
@router.get("/me", status_code=status.HTTP_200_OK, response_model="")
async def get_current_user(
    user=Depends(get_current_user), _: bool = Depends(role_checker)
):
    return user


@router.get(
    "/logout",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logged Out successfully",
                    }
                }
            },
        }
    },
)
async def revoke_token(token_details: dict = Depends(RefreshTokenBearer())):
    jti = token_details["jti"]
    await add_jti_to_blocklist(jti)
    return {"message": "Logged Out Successfully"}


@router.get(
    "/passwords/reset",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Please check your email for instructions to reset your password",
                    }
                }
            },
        }
    },
)
async def password_reset_request(
    email_data: PasswordResetModel,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    email = email_data.email
    user = UserService.get_user_by_email(email)
    otp = generate_otp(user, session)
    send_email(
        background_tasks,
        "Reset Your Password",
        user.email,
        {"name": user.first_name, "otp": str(otp)},
        "password_reset_email.html",
    )

    return {
        "message": "Please check your email for instructions to reset your password",
    }


@router.get(
    "/passwords/reset/verify",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "OTP verified, proceed to set a new password",
                    }
                }
            },
        }
    },
)
async def password_reset_verify_otp(
    data: PasswordResetVerifyOtpModel,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    email = data.email
    otp = data.otp

    user = await user_service.get_user_by_email(email, session)

    if not user:
        raise UserNotFound()

    otp_record = await user_service.get_otp_by_user(user_id, otp, session)
    user_id = user.id

    if not otp_record or not otp_record.is_valid:
        raise InvalidOtp()

    # Clear OTP after verification
    invalidate_previous_otps(user, session)

    send_email(
        background_tasks,
        "Verify your email",
        user.email,
        {"name": user.first_name},
        "welcome_message",
    )

    return {
        "message": "OTP verified, proceed to set a new password",
    }


@router.get(
    "/passwords/reset/complete",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Your password has been reset, proceed to login",
                    }
                }
            },
        }
    },
)
async def password_reset_done(
    data: PasswordResetConfirmModel,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    email = data.email
    new_password = data.new_password

    user = await user_service.get_user_by_email(email, session)

    if not user:
        raise UserNotFound()

    passwd_hash = hash_password(new_password)
    await user_service.update_user(user, {"password_hash": passwd_hash}, session)
    send_email(
        background_tasks,
        "Password Reset Successful",
        user.email,
        {"name": user.first_name},
        "password_reset_success.html",
    )

    return {
        "message": "Your password has been reset, proceed to login",
    }


@router.get("/passwords/change")
async def password_change(
    data: PasswordChangeModel, session: AsyncSession = Depends(get_session)
):
    pass


@router.get("/signup/google")
async def google_oauth_signup():
    pass


@router.get("/login/google")
async def google_oauth_login():
    pass
