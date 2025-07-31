from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.exceptions import HTTPException
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
    UserCreate,
    UserLoginModel,
    UserResponse,
)
from src.auth.service import UserService
from src.auth.utils import generate_otp, hash_password, invalidate_previous_otps
from src.db.main import get_session
from src.db.models import Profile, User
from src.errors import InvalidOtp, UserNotFound
from src.mail import send_email

router = APIRouter()

user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


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


@router.get("/verification/verify", status_code=status.HTTP_200_OK)
async def verify_user_account(
    data: OtpVerify,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    # get the email and otp
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


@router.get("/verification")
async def resend_verification_email(
    token: str, session: AsyncSession = Depends(get_session)
):
    pass


str


@router.get("/token")
async def login_user(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    pass


@router.get("/token/refresh")
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer)):
    pass


@router.get("/me")
async def get_current_user(
    user=Depends(get_current_user), _: bool = Depends(role_checker)
):
    pass


@router.get("/logout")
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
    pass


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
