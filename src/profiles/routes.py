from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.utils import SUCCESS_EXAMPLE
from src.cloudinary_service import CloudinaryService
from src.db.main import get_session
from src.db.models import Profile, ProfileSkill, User
from src.errors import InsufficientPermission, NotFound, UnprocessableEntity
from src.profiles.schema_examples import (
    ADD_SKILL_RESPONSES,
    DELETE_SKILL_RESPONSES,
    GET_USER_PROFILE_EXAMPLE,
    GET_USER_PROFILE_RESPONSES,
    GET_USER_SKILLS_RESPONSES,
    UPDATE_PROFILE_RESPONSES,
    UPDATE_SKILL_RESPONSES,
    UPLOAD_AVATAR_RESPONSES,
)
from src.profiles.schemas import (
    AvatarUploadResponse,
    ProfileData,
    ProfileListData,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdate,
    SkillCreate,
    SkillData,
    SkillResponse,
    SkillUpdate,
)
from src.profiles.service import ProfileService

router = APIRouter()

profile_service = ProfileService()
cloudinary_service = CloudinaryService()


@router.get("/", response_model=ProfileListResponse)
async def get_profiles(
    search: str = Query(None, description="Search by username, intro, or location"),
    limit: int = Query(20, ge=1, le=100, description="Number of profiles to return"),
    offset: int = Query(0, ge=0, description="Number of profiles to skip"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all profiles with optional search and pagination

    EXAMPLE:
    - GET /profiles/ → Returns first 20 profiles
    - GET /profiles/?search=python → Returns profiles mentioning "python"
    - GET /profiles/?limit=10&offset=20 → Returns profiles 21-30
    """
    profiles = await profile_service.get_all_profiles(
        session=session, search=search, limit=limit, offset=offset
    )

    # Convert to response format (add user data)
    response = []
    for profile in profiles:
        response.append(
            ProfileListResponse(
                status=SUCCESS_EXAMPLE,
                message="Profiles retrieved successfully",
                data=ProfileListData(
                    id=str(profile.id),
                    user_id=str(profile.user_id),
                    username=profile.user.username,
                    full_name=profile.user.full_name,
                    short_intro=profile.short_intro,
                    location=profile.location,
                    avatar_url=profile.avatar_url,
                ),
            )
        )

    return response


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
    responses=UPLOAD_AVATAR_RESPONSES,
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


@router.get(
    "/{username}", response_model=ProfileResponse, responses=GET_USER_PROFILE_EXAMPLE
)
async def get_user_profile(
    username: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific user's profile by their username

    EXAMPLE:
    - GET /profiles/johndoe → Returns johndoe's profile
    """
    profile = await profile_service.get_profile_by_username(username, session)

    if not profile:  # sanme as if profile is None
        raise NotFound("Profile for user '{username}' not found")

    return {
        "status": SUCCESS_EXAMPLE,
        "message": "Profile retrieved successfully",
        "data": profile,
    }


@router.patch(
    "/{username}",
    responses=UPLOAD_AVATAR_RESPONSES,
    response_model=ProfileResponse,
)
async def update_user_profile(
    username: str,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update a user's profile

    EXAMPLE:
    - PATCH /profiles/johndoe with {"bio": "New bio"} → Updates johndoe's bio
    """
    if current_user.username != username:
        raise InsufficientPermission(message="You can only update your own profile")

    profile = await profile_service.get_profile_by_username(username, session)
    if not profile:
        raise NotFound("Profile for user '{username}' not found")

    update_data = profile_data.model_dump(exclude_unset=True)
    updated_profile = await profile_service.update_profile(
        profile, update_data, session
    )

    return updated_profile


@router.post(
    "/{username}/skills",
    responses=ADD_SKILL_RESPONSES,
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_skill_to_profile(
    username: str,
    skill_data: SkillCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Add a new skill to user's profile

    EXAMPLE:
    - POST /profiles/johndoe/skills with {"name": "Python", "description": "5 years"}
    - Creates link between johndoe and Python skill
    """

    if current_user.username != username:
        raise InsufficientPermission(
            message="You can only add skills to your own profile"
        )

    profile = await profile_service.get_profile_by_username(username, session)
    if not profile:
        raise NotFound("Profile for user '{username}' not found")

    try:
        profile_skill = await profile_service.add_skill_to_profile(
            profile_id=str(profile.id),
            skill_name=skill_data.name,
            description=skill_data.description,
            session=session,
        )
    except ValueError as e:
        raise UnprocessableEntity(str(e))

    return SkillResponse(
        status=SUCCESS_EXAMPLE,
        message="Skill added to profile successfully",
        data=SkillData(
            id=str(profile_skill.id),
            name=profile_skill.skill.name,
            description=profile_skill.description,
            created_at=profile_skill.created_at,
        ),
    )


@router.get("/{username}/skills", 
            responses=GET_USER_SKILLS_RESPONSES,
            response_model=List[SkillResponse])
async def get_user_skills(
    username: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get all skills for a specific user

    EXAMPLE:
    - GET /profiles/johndoe/skills
    - Returns: [{"name": "Python", "description": "5 years"}, ...]
    """
    profile = await profile_service.get_profile_by_username(username, session)
    if not profile:
        raise NotFound("Profile for user '{username}' not found")

    skills = await profile_service.get_profile_skills(str(profile.id), session)

    return [
        SkillResponse(
            status=SUCCESS_EXAMPLE,
            message="Skills retrieved successfully",
            data=SkillData(
                id=str(skill.id),
                name=skill.skill.name,
                description=skill.description,
                created_at=skill.created_at,
            ),
        )
        for skill in skills
    ]


@router.patch("/{username}/skills/{skill_id}", 
              responses=UPDATE_SKILL_RESPONSES,
              response_model=SkillResponse)
async def update_skill(
    username: str,
    skill_id: str,
    skill_data: SkillUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update a specific skill in user's profile

    EXAMPLE:
    - PATCH /profiles/johndoe/skills/123 with {"description": "10 years"}
    - Updates description of skill 123 in johndoe's profile
    """
    if current_user.username != username:
        raise InsufficientPermission(message="You can only update your own skills")

    profile = await profile_service.get_profile_by_username(username, session)
    if not profile:
        raise NotFound("Profile for user '{username}' not found")

    profile_skill = await profile_service.get_profile_skill(
        skill_id=skill_id, profile_id=str(profile.id), session=session
    )

    if not profile_skill:
        raise NotFound("Skill not found in profile")

    update_data = skill_data.model_dump(exclude_unset=True)
    updated_skill = await profile_service.update_profile_skill(
        profile_skill, update_data, session
    )

    return SkillResponse(
        status=SUCCESS_EXAMPLE,
        message="Skill updated successfully",
        data=SkillData(
            id=str(updated_skill.id),
            name=updated_skill.skill.name,
            description=updated_skill.description,
            created_at=updated_skill.created_at,
        ),
    )


@router.delete("/{username}/skills/{skill_id}", 
               responses=DELETE_SKILL_RESPONSES,
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    username: str,
    skill_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Remove a skill from user's profile

    NOTE: This only removes the link, not the skill itself
    - Skill still exists in Skills table
    - Other users can still have this skill

    EXAMPLE:
    - DELETE /profiles/johndoe/skills/123
    - Removes skill 123 from johndoe's profile
    """

    if current_user.username != username:
        raise InsufficientPermission("You can only delete your own skills")

    profile = await profile_service.get_profile_by_username(username, session)
    if not profile:
        raise NotFound(f"Profile for user '{username}' not found")

    profile_skill = await profile_service.get_profile_skill(
        skill_id=skill_id, profile_id=str(profile.id), session=session
    )

    if not profile_skill:
        raise NotFound("Skill not found in profile")

    await profile_service.delete_profile_skill(profile_skill, session)

    return None


# TODO: SECURITY CHECK FOR THE RESPONSES
