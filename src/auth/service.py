from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.schemas import UserCreate
from src.auth.utils import hash_password
from src.db.models import Otp, Profile, User


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

        return new_user

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.items():
            setattr(user, k, v)

        await session.commit()
        return user
