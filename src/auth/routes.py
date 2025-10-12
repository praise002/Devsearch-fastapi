import logging
from datetime import datetime

from decouple import config
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import RefreshTokenBearer, RoleChecker, get_current_user
from src.auth.oauth_config import oauth
from src.auth.schemas import (
    OtpVerify,
    PasswordChangeModel,
    PasswordResetConfirmModel,
    PasswordResetModel,
    PasswordResetVerifyOtpModel,
    SendOtp,
    SkillResponse,
    UserCreate,
    UserLoginModel,
    UserRegistrationResponse,
    UserResponse,
)
from src.auth.service import UserService
from src.auth.utils import (
    ACCESS_TOKEN_EXAMPLE,
    REFRESH_TOKEN_EXAMPLE,
    UUID_EXAMPLE,
    generate_otp,
    hash_password,
    invalidate_previous_otps,
    verify_password,
)
from src.config import Config
from src.db.main import get_session
from src.db.models import User
from src.db.redis import add_jti_to_blocklist
from src.errors import (
    AccountNotVerified,
    GoogleAuthenticationFailed,
    InvalidOldPassword,
    InvalidOtp,
    InvalidToken,
    PasswordMismatch,
    UserAlreadyExists,
    UserNotActive,
    UserNotFound,
)
from src.mail import send_email

router = APIRouter()

user_service = UserService()
role_checker = RoleChecker(["admin", "user"])
REFRESH_TOKEN = Config.REFRESH_TOKEN_EXPIRY

# TODO: ADD MORE EXAMPLES

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegistrationResponse,
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
        raise UserAlreadyExists()

    username = user_data.username
    username_exists = await user_service.username_exists(username, session)
    if username_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User with username already exists.",
        )

    new_user = await user_service.create_user(user_data, session)

    otp = generate_otp(new_user, session)
    send_email(
        background_tasks,
        "Verify your email",
        new_user.email,
        {"name": new_user.first_name, "otp": str(otp)},
        "verify_email_request.html",
    )

    return {
        "status": "success",
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
            "status": "success",
            "message": "Email address already verified. No OTP sent",
        }

    user_service.update_user(user, {"is_email_verified": True}, session)

    invalidate_previous_otps(user, session)

    send_email(
        background_tasks,
        "Account Verified",
        user.email,
        {"name": user.first_name},
        "welcome_message",
    )

    return {
        "status": "success",
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

    if (
        user is None
        or user.hashed_password is None
        or not verify_password(password, user.password_hash)
    ):
        return JSONResponse(
            content={
                "status": "failure",
                "message": "No active account found with the given credentials",
                "error_code": "unauthorized",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_email_verified:
        raise AccountNotVerified()

    if not user.is_active:
        raise UserNotActive()

    password_valid = verify_password(password, user.password_hash)
    if password_valid:
        user_data = user_data = {
            "email": user.email,
            "user_id": str(user.id),
            "role": user.role,
        }
        tokens = user_service.create_token_pair(user_data)

        return {
            "status": "success",
            "message": "Login successful",
            **tokens,
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
async def refresh_token(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(RefreshTokenBearer()),
):
    old_jti = token_details["jti"]
    await user_service.blacklist_user_token(old_jti, session)

    await add_jti_to_blocklist(old_jti)
    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_token = user_service.create_token_pair(
            token_details["user"],
        )

        return {
            "status": "success",
            "message": "Token refreshed successfully",
            **new_token,
        }

    raise InvalidToken()


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    description="This endpoint returns the authenticated user's profile information.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "id": UUID_EXAMPLE,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "username": "johndoe",
                        "short_intro": "Full-stack developer passionate about building scalable web applications",
                        "bio": "I'm a software engineer with 5+ years of experience in Python, JavaScript, and cloud technologies. I love contributing to open-source projects and mentoring junior developers.",
                        "location": "San Francisco, CA",
                        "avatar_url": "https://example.com/avatars/johndoe.jpg",
                        "github": "https://github.com/johndoe",
                        "stack_overflow": "https://stackoverflow.com/users/12345/johndoe",
                        "tw": "https://twitter.com/johndoe",
                        "ln": "https://linkedin.com/in/johndoe",
                        "website": "https://johndoe.dev",
                        "skills": [
                            {
                                "id": UUID_EXAMPLE,
                                "name": "Python",
                                "description": "Expert level proficiency in Python development",
                            },
                            {
                                "id": UUID_EXAMPLE,
                                "name": "FastAPI",
                                "description": "Advanced knowledge of FastAPI framework",
                            },
                            {
                                "id": UUID_EXAMPLE,
                                "name": "React",
                                "description": "Intermediate level React development skills",
                            },
                        ],
                    }
                }
            }
        },
        401: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "message": "Please provide a valid access token.",
                        "resolution": "Please get an access token",
                        "error_code": "access_token_required",
                    }
                }
            }
        },
    },
)
async def get_current_user_endpoint(
    current_user=Depends(get_current_user),
    _: bool = Depends(role_checker),
    session: AsyncSession = Depends(get_session),
):
    statement = (
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == current_user.id)
    )
    result = await session.exec(statement)
    user = result.first()
    profile = user.profile
    skill = profile.skill
    profile_skill = skill.profile_skill

    if not user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="User not found"
        )

    return UserResponse(
        # User fields
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        # Profile fields
        short_intro=profile.short_intro,
        bio=profile.bio,
        location=profile.location,
        github=profile.github,
        stack_overflow=profile.stack_overflow,
        tw=profile.tw,
        ln=profile.ln,
        website=profile.website,
        skills=SkillResponse(
            id=skill.id,
            name=skill.name,
            description=profile_skill.description,
        ),
    )


@router.post(
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
async def revoke_token(
    token_details: dict = Depends(RefreshTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    jti = token_details["jti"]
    await user_service.blacklist_user_token(jti, session)
    return {"status": "success", "message": "Logged Out Successfully"}


@router.post(
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
        "status": "success",
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
        "status": "success",
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
        "status": "success",
        "message": "Your password has been reset, proceed to login",
    }


@router.post("/passwords/change", status_code=status.HTTP_200_OK)
async def password_change(
    data: PasswordChangeModel,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if data.new_password != data.confirm_password:
        raise PasswordMismatch()

    user = await user_service.get_user_by_email(current_user.email, session)

    if not verify_password(data.old_password, user.hashed_password):
        raise InvalidOldPassword()

    hashed_password = hash_password(data.new_password)
    await user_service.update_user(user, {"hashed_password": hashed_password})

    await user_service.blacklist_all_user_tokens(user.id)  # or str(user.id)

    user_data = {
        "email": user.email,
        "user_id": str(user.id),
        "role": user.role,
    }
    tokens = user_service.create_token_pair(user_data)

    return {
        "status": "success",
        "message": "Password changed successfully",
        **tokens,
    }  # TODO: USE HTTP-COOKIE LATER


@router.post(
    "/logout/all",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logged out of all devices successfully",
                    }
                }
            },
        }
    },
)
async def revoke_all(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await user_service.blacklist_all_user_tokens(user.id, session)
    return {"status": "success", "message": "Logged out of all devices successfully"}


@router.get(
    "/google",
    status_code=status.HTTP_302_FOUND,
    description="""
    **Google OAuth Authentication**
    
    This endpoint initiates Google OAuth authentication flow.
    
    Important for API Documentation Users:
    - This endpoint performs a redirect to Google's authentication page
    - Redirects do not work properly in Swagger UI/API documentation
    - To test this endpoint:
      1. Copy the full URL: `http://127.0.0.1:7000/api/v1/auth/google`
      2. Paste it directly into your browser address bar
      3. You will be redirected to Google for authentication
      4. After authentication, you'll be redirected back to the callback URL
    """,
    responses={302: {"description": "Redirect to Google OAuth authorization page"}},
)
async def google_auth(request: Request):
    """Redirect user to Google for authorization"""
    redirect_url = config("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_url)


@router.get("/google/callback", status_code=status.HTTP_200_OK, include_in_schema=False)
async def google_auth_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Handle Google OAuth callback - this is where you get tokens"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        email = user_info.get("email")
        AUTH_PROVIDER = "google"

        existing_user = await user_service.get_user_by_email(email, session)

        if existing_user and existing_user.auth_provider == AUTH_PROVIDER:
            tokens = await user_service.handle_oauth_user_login(existing_user, session)

            access = tokens["access"]
            refresh = tokens["refresh"]

            frontend_callback_url = config("FRONTEND_CALLBACK_URL")
            redirect_url = (
                f"{frontend_callback_url}"
                f"?access={access}&refresh={refresh}&is_new=true"
            )
            return RedirectResponse(redirect_url)

        else:
            first_name = user_info.get("given_name")
            last_name = user_info.get("family_name")
            # download and upload image to cloudinary
            # picture = user_info.get("picture") TODO: LATER
            auth_provider = user_info.get("iss")
            print(auth_provider)
            google_id = user_info.get("sub")
            username = email.split("@")[0]
            user_create_obj = UserCreate(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                google_id=google_id,
                auth_provider=AUTH_PROVIDER,
            )

            new_user, response = await user_service.handle_oauth_user_register(
                user_create_obj, session
            )

            send_email(
                background_tasks,
                "Welcome",
                new_user.email,
                {"name": new_user.first_name},
                "welcome_message",
            )

            return response

    except Exception as e:
        logging.exception(f"Google authentication failed: {str(e)}")
        raise GoogleAuthenticationFailed()


#  user_info = await oauth.google.parse_id_token(request, token)
