from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.schemas import UserCreate
from src.auth.service import UserService
from src.db.main import get_session

router = APIRouter()

user_service = UserService()


@router.post("/register")
async def create_user_account(
    user_data: UserCreate, session: AsyncSession = Depends(get_session)
):
    # Check if user exists
    email = user_data.email
    user_exist = await user_service.user_exists(email, session)
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    new_user = await user_service.create_user(user_data, session)

    return {
        "message": "Account Created! Check email to verify your account",
        "user": new_user,
    }
