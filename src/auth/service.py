from datetime import datetime, timezone

from decouple import config
from fastapi.responses import RedirectResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.schemas import UserCreate
from src.auth.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from src.db.models import BlacklistedToken, Otp, OutstandingToken, Profile, User
from src.db.redis import add_jti_to_blocklist, token_in_blacklist
from src.errors import InvalidToken, UserNotActive


class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def get_user_by_username(self, username: str, session: AsyncSession):
        statement = select(User).where(User.username == username)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def get_otp_by_user(self, user_id: str, otp: int, session: AsyncSession):
        statement = select(Otp).where(Otp.user_id == user_id, Otp.otp == otp)
        result = await session.exec(statement)
        otp_record = result.first()
        return otp_record

    async def user_exists(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def username_exists(self, username: str, session: AsyncSession):
        user = await self.get_user_by_username(username, session)
        return user is not None

    async def create_user(self, user_data: UserCreate, session: AsyncSession):
        extra_data = {}
        if user_data.password:
            extra_data["hashed_password"] = hash_password(user_data.password)

        else:
            extra_data["hashed_password"] = None

        new_user = User.model_validate(user_data, update=extra_data)
        
        if user_data.auth_provider:
            new_user.is_email_verified = True

        session.add(new_user)

        await session.commit()
        await session.refresh(new_user)

        profile = Profile(user_id=new_user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        return new_user

    async def handle_oauth_user_login(self, user: User, session: AsyncSession) -> dict:
        """
        Handle OAuth user login, ensuring email verification and active status.

        Args:
            user: The authenticated user from OAuth provider
            session: Database session

        Returns:
            dict: Token pair (access_token, refresh_token)

        Raises:
            UserNotActive: If user account is disabled
        """
        if not user.is_email_verified:
            user.is_email_verified = True
            session.add(user)
            await session.commit()
            await session.refresh(user)

        if not user.is_active:
            raise UserNotActive()

        # login user
        user_data = {
            "email": user.email,
            "user_id": str(user.id),
            "role": user.role,
        }

        return self.create_token_pair(user_data)

    async def handle_oauth_user_register(
        self, user_create_data, user_data, session: AsyncSession
    ) -> dict:
        new_user = self.create_user(user_create_data, user_data, session)
        tokens = self.create_token_pair(user_data)
        access = tokens["access"]
        refresh = tokens["refresh"]

        frontend_callback_url = config("FRONTEND_CALLBACK_URL")
        redirect_url = f"{frontend_callback_url}" f"?access={access}&is_new=true"

        response = RedirectResponse(redirect_url)
        response.set_cookie(
            key="refresh",
            value=refresh,
            httponly=True,
            secure=True,  # Ensure you're using HTTPS
            samesite="None",
        )

        return new_user, response

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.items():
            setattr(user, k, v)

        await session.commit()
        return user

    async def create_outstanding_token(
        self, user_id: str, jti: str, expires_at: datetime, session: AsyncSession
    ):
        """Store a token's JTI as an outstanding (active) token"""
        outstanding_token = OutstandingToken(
            user_id=user_id, jti=jti, expires_at=expires_at
        )
        session.add(outstanding_token)
        await session.commit()
        session.refresh(outstanding_token)
        return outstanding_token

    async def blacklist_user_token(self, jti: str, session: AsyncSession):
        statement = select(OutstandingToken).where(OutstandingToken.jti == jti)
        result = await session.exec(statement)
        token_record = result.first()

        blacklisted_token = BlacklistedToken(token_id=token_record.id)
        session.add(blacklisted_token)

        # Also add to Redis for fast lookup during requests
        await add_jti_to_blocklist(jti)

        await session.commit()

    async def blacklist_all_user_tokens(self, user_id: str, session: AsyncSession):
        """Move all user tokens from outstanding to blacklisted"""

        statement = select(OutstandingToken).where(OutstandingToken.user_id == user_id)
        result = await session.exec(statement)
        user_tokens = result.all()

        for token_record in user_tokens:
            blacklisted_token = BlacklistedToken(token_id=token_record.id)
            session.add(blacklisted_token)

            # Also add to Redis for fast lookup during requests
            await add_jti_to_blocklist(token_record.jti)

        await session.commit()

    async def is_token_blacklisted(self, jti: str, session: AsyncSession) -> bool:
        """Check if a token JTI is blacklisted"""
        if await token_in_blacklist(jti):
            return True

        # fallback
        statement = (
            select(BlacklistedToken)
            .join(OutstandingToken)
            .where(OutstandingToken.jti == jti)
        )
        result = await session.exec(statement)
        blacklisted_record = result.first()

        return blacklisted_record is not None

    async def cleanup_expired_tokens(self, session: AsyncSession):
        """Remove expired tokens from outstanding tokens table"""
        now = datetime.now(timezone.utc)
        statement = select(OutstandingToken).where(OutstandingToken.expires_at < now)
        result = await session.exec(statement)
        expired_tokens = result.all()

        for token in expired_tokens:
            await session.delete(token)

        await session.commit()

    async def cleanup_blacklisted_tokens(self, session: AsyncSession):
        """Remove blacklisted tokens from blacklisted tokens table"""
        statement = select(BlacklistedToken)
        result = await session.exec(statement)
        blacklisted_tokens = result.all()

        for token in blacklisted_tokens:
            await session.delete(token)

        await session.commit()

    async def create_token_pair(self, user_data: dict, session: AsyncSession) -> dict:
        """Create both access and refresh tokens"""
        refresh_token = create_refresh_token(user_data)

        refresh_payload = decode_token(refresh_token)
        refresh_jti = refresh_payload["jti"]
        expires_at = datetime.fromtimestamp(refresh_payload["exp"])

        await self.create_outstanding_token(
            user_id=user_data["user_id"],
            jti=refresh_jti,
            expires_at=expires_at,
            session=session,
        )

        access_token = create_access_token(user_data)

        return {
            "access": access_token,
            "refresh": refresh_token,
        }

    async def validate_token(self, token: str, session: AsyncSession):
        payload = decode_token(token)
        jti = payload["jti"]

        user_service = UserService()
        if await user_service.is_token_blacklisted(jti, session):
            raise InvalidToken()

        return payload
