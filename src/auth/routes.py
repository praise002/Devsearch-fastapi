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
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
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


@router.get(
    "/verification/verify",
    status_code=status.HTTP_200_OK,
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
        "message": "Email verified successfully",
    }


@router.get(
    "/verification",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "OTP sent successfully",
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
        "message": "OTP sent successfully",
    }


@router.get(
    "/token",
    status_code=status.HTTP_200_OK,
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
        }
    },
)
async def login_user(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    email = login_data.email
    password = login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user is not None:

        if not user.is_email_verified:
            return JSONResponse(
                content={
                    "message": "Email not verified. Please verify your email before logging in"
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_active:
            return JSONResponse(
                content={
                    "message": "Your account has been disabled. Please contact support for assistance"
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


@router.get(
    "/token/refresh",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Token refreshed successfully",
                        "access_token": ACCESS_TOKEN_EXAMPLE,
                    }
                }
            },
        }
    },
)
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(user_data=token_details["user"])
        return {
            "message": "Token refreshed successfully",
            "access_token": new_access_token,
        }

    raise InvalidToken()


# TODO: PUT THE RESPONSE MODEL LATER
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
                        "message": "TLogged Out successfully",
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


@router.get("/passwords/reset")
async def password_reset_request(email_data: PasswordResetModel):
    pass


@router.get("/passwords/reset/verify")
async def password_reset_verify_otp(data: PasswordResetVerifyOtpModel):
    pass


@router.get("/passwords/reset/complete")
async def password_reset_done(
    passwords: PasswordResetConfirmModel, session: AsyncSession = Depends(get_session)
):
    pass


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
