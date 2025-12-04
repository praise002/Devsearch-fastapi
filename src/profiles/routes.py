# - `GET /api/v1/profiles/` - List profiles
# - `PATCH /api/v1/profiles/avatar/` - Update user avatar
# - `DELETE /api/v1/profiles/avatar/` - Delete user avatar
# - `GET /api/v1/profiles/{username}` - Get user profile
# - `PATCH /api/v1/profiles/{username}` - Update user profile
# - `POST /api/v1/profiles/{username}/skills` - Add skill
# - `PATCH /api/v1/profiles/{username}/skills` - Update a specific skill e.g adding description
# - `GET /api/v1/profiles/skills` - Retrieve a list of skills
# - `DELETE /api/v1/profiles/{username}/skills/{skill_id}` - Remove skill
import logging

from fastapi import APIRouter, Depends, FastAPI, File, UploadFile, status
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.utils import SUCCESS_EXAMPLE
from src.cloudinary_service import CloudinaryService
from src.db.main import get_session
from src.db.models import Profile, ProfileSkill, User
from src.errors import NotFound
from src.profiles.schema_examples import (
    GET_USER_PROFILE_RESPONSES,
    UPDATE_PROFILE_RESPONSES,
)
from src.profiles.schemas import (
    AvatarUploadResponse,
    ProfileData,
    ProfileResponse,
    ProfileUpdate,
    SkillResponse,
)
from src.profiles.service import ProfileService

router = APIRouter()

profile_service = ProfileService()
cloudinary_service = CloudinaryService()


@router.get(
    "/me",
    response_model=ProfileResponse,
    responses=GET_USER_PROFILE_RESPONSES,
)
async def get_my_profile(
    current_user=Depends(get_current_user),
    # _: bool = Depends(role_checker),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's profile"""
    statement = (
        select(User)
        .options(
            selectinload(User.profile)
            .selectinload(Profile.skills)
            .selectinload(ProfileSkill.skill)
        )
        .where(User.id == current_user.id)
    )

    result = await session.exec(statement)
    user = result.first()

    if not user:
        raise NotFound(
            "Profile not found",
        )

    profile = user.profile

    skills_response = []

    if profile.skills:
        for profile_skill in profile.skills:
            if profile_skill.skill:
                skills_response.append(
                    SkillResponse(
                        id=profile_skill.skill.id,
                        name=profile_skill.skill.name,
                        description=profile_skill.description,
                    )
                )

    return ProfileResponse(
        status="success",
        message="Profile retrieved successfully",
        data=ProfileData(
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
            skills=skills_response,
        ),
    )


@router.patch(
    "/me",
    responses=UPDATE_PROFILE_RESPONSES,
    response_model=ProfileResponse,
)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update current user's profile"""
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if not profile:
        raise NotFound("Profile not found")

    update_data = profile_data.model_dump(exclude_unset=True)
    updated_profile = await profile_service.update_profile(
        profile, update_data, session
    )

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Profile updated successfully",
        "data": updated_profile,
    }


@router.post(
    "/avatar",
    response_model=AvatarUploadResponse,
)
async def upload_avatar(
    file: UploadFile = File(description="Avatar image file"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload or update user's avatar image

    - **file**: Image file (jpg, jpeg, png, webp)
    - Maximum file size: 5MB
    - Image will be automatically cropped to 500x500 and optimized
    """

    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if not profile:
        raise NotFound("Profile not found")

    # Upload to Cloudinary with user-specific public_id
    public_id = f"user_{current_user.id}"
    upload_result = await cloudinary_service.upload_image(
        file=file, public_id=public_id
    )

    # Update profile with new avatar URL
    updated_profile = await profile_service.update_avatar(
        profile, upload_result["url"], session
    )

    return AvatarUploadResponse(
        status="success",
        message="Avatar uploaded successfully",
        avatar_url=updated_profile.avatar_url,
    )


@router.delete(
    "/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=UPDATE_PROFILE_RESPONSES,
)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete user's avatar"""
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    if not profile:
        raise NotFound("Profile not found")

    # Delete from Cloudinary
    public_id = cloudinary_service.extract_public_id_from_url(profile.avatar_url)
    if public_id:
        await cloudinary_service.delete_image(public_id)

    # Reset to default avatar
    profile.avatar_url = None
    session.add(profile)
    await session.commit()

    return


# NOTE: CAN RETURN 204 AND FRONTEND SHOULD BE ABLE TO DISPLAY DEFAULT URL


# NOTE: CAN RETURN 204 AND FRONTEND SHOULD BE ABLE TO DISPLAY DEFAULT URL
