from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.schemas import UserCreate
from src.auth.utils import hash_password
from src.db.models import Profile, User


class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def user_exists(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def create_user(self, user_data: UserCreate, session: AsyncSession):
        user_data_dict = user_data.model_dump()  # convert to dict
        new_user = User(**user_data_dict)  # unpacking it
       
        print(new_user)
        hashed_password = hash_password(user_data_dict["password"])
        new_user.hashed_password = hashed_password

        new_profile = Profile(
            user=new_user,
        )
        print(new_profile)

        session.add(new_profile)
        await session.commit()
        return new_profile

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.ittems():
            setattr(user, k, v)

        await session.commit()
        return user
