from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.exceptions import HTTPException
from fastapi_mail import FastMail, MessageSchema, MessageType

from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import (
    AccessTokenBearer,
    RefreshTokenBearer,
    RoleChecker,
    get_current_user,
)
from src.auth.schemas import (
    PasswordChangeModel,
    PasswordResetConfirmModel,
    PasswordResetModel,
    PasswordResetVerifyOtpModel,
    UserCreate,
    UserLoginModel,
    UserResponse,
)
from src.auth.service import UserService
from src.auth.utils import generate_otp, hash_password
from src.config import conf
from src.db.main import get_session
from src.db.models import Profile, User

router = APIRouter()

user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


def send_email(
    background_tasks: BackgroundTasks,
    subject: str,
    email_to: str,
    template_context: dict,
):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=template_context,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    background_tasks.add_task(
        fm.send_message,
        message,
        template_name="verify_email_request.html",
    )


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
    )

    return {
        "message": "Account Created! Check email to verify your account",
        "email": new_user.email,
    }


@router.get("/verification/verify")
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):
    pass


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
