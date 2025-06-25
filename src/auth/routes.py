from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.schemas import UserCreate
from src.auth.utils import hash_password
from src.db.main import get_session
from src.db.models import Profile, User

router = APIRouter()


async def get_user_by_email(email: str, session: AsyncSession):
    statement = select(User).where(User.email == email)
    result = await session.exec(statement)
    user = result.first()
    return user


async def user_exists(email, session: AsyncSession):
    user = await get_user_by_email(email, session)
    return user is not None


@router.post("/register")
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    # Check if user exists
    user_exist = await user_exists(user.email, session)
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password & save user
    hashed_password = hash_password(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )

    new_profile = Profile(
        user=new_user,
    )

    session.add(new_profile)
    await session.commit()

    return {
        "message": "Account Created! Check email to verify your account",
        "user": new_user,
    }
