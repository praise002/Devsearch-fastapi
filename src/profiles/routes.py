from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import SUCCESS_EXAMPLE
from src.cloudinary_service import CloudinaryService
from src.db.main import get_session
from src.db.models import Profile, ProfileSkill, User
from src.errors import NotFound, UnprocessableEntity
from src.profiles.schema_examples import (
    ADD_SKILL_RESPONSES,
    DELETE_AVATAR_RESPONSES,
    DELETE_SKILL_RESPONSES,
    GET_USER_PROFILE_RESPONSES,
    GET_USER_PROFILES_RESPONSES,
    GET_USER_SKILLS_RESPONSES,
    UPDATE_PROFILE_RESPONSES,
    UPDATE_SKILL_RESPONSES,
    UPLOAD_AVATAR_RESPONSES,
)
from src.profiles.schemas import (
    AvatarUploadResponse,
    PaginationData,
    ProfileData,
    ProfileListResponse,
    ProfileListResult,
    ProfileResponse,
    ProfileUpdate,
    SkillCreate,
    SkillData,
    SkillDataResponse,
    SkillListResponse,
    SkillResponse,
    SkillUpdate,
)
from src.profiles.service import ProfileService

router = APIRouter()

profile_service = ProfileService()
cloudinary_service = CloudinaryService()


def profile_response(message, profile_with_user, skills_response):
    return ProfileResponse(
        status=SUCCESS_EXAMPLE,
        message=message,
        data=ProfileData(
            # User fields
            id=str(profile_with_user.user_id),
            email=profile_with_user.user.email,
            first_name=profile_with_user.user.first_name,
            last_name=profile_with_user.user.last_name,
            username=profile_with_user.user.username,
            # Profile fields
            short_intro=profile_with_user.short_intro,
            bio=profile_with_user.bio,
            location=profile_with_user.location,
            avatar_url=profile_with_user.avatar_url,
            github=profile_with_user.github,
            stack_overflow=profile_with_user.stack_overflow,
            tw=profile_with_user.tw,
            ln=profile_with_user.ln,
            website=profile_with_user.website,
            skills=skills_response,
        ),
    )


@router.get(
    "/", response_model=ProfileListResponse, responses=GET_USER_PROFILES_RESPONSES
)
async def get_profiles(
    request: Request,
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
    profiles, total_count = await profile_service.get_all_profiles(
        session=session, search=search, limit=limit, offset=offset
    )

    # Build pagination URLs
    base_url = str(request.url).split("?")[0]
    query_params = {}

    if search:
        query_params["search"] = search

    # Next page URL
    next_offset = offset + limit
    if next_offset < total_count:
        next_params = query_params.copy()
        next_params["limit"] = limit
        next_params["offset"] = next_offset
        next_url = f"{base_url}?{urlencode(next_params)}"
    else:
        next_url = None

    # Previous page URL
    previous_offset = offset - limit
    if offset > 0:
        previous_params = query_params.copy()
        previous_params["limit"] = limit
        previous_params["offset"] = max(0, previous_offset)
        previous_url = f"{base_url}?{urlencode(previous_params)}"
    else:
        previous_url = None

    profiles_data = [
        ProfileListResult(
            id=str(profile.id),
            user_id=str(profile.user_id),
            username=profile.user.username,
            full_name=profile.user.full_name,
            short_intro=profile.short_intro,
            location=profile.location,
            avatar_url=profile.avatar_url,
        )
        for profile in profiles
    ]

    return ProfileListResponse(
        status="success",
        message="Profiles retrieved successfully",
        data=PaginationData(
            count=total_count,
            next=next_url,
            previous=previous_url,
            results=profiles_data,
        ),
    )


@router.get(
    "/me",
    response_model=ProfileResponse,
    responses=GET_USER_PROFILE_RESPONSES,
)
async def get_my_profile(
    current_user=Depends(get_current_user),
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

    profile = user.profile

    skills_response = []

    if profile.skills:
        for profile_skill in profile.skills:
            if profile_skill.skill:
                skills_response.append(
                    SkillDataResponse(
                        id=str(profile_skill.skill.id),
                        name=profile_skill.skill.name,
                        description=profile_skill.description,
                    )
                )

    return profile_response("Profile retrieved successfully", user, skills_response)


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

    update_data = profile_data.model_dump(exclude_unset=True)
    updated_profile = await profile_service.update_profile(
        profile, update_data, session
    )

    # Refresh the profile with user relationship loaded
    statement = (
        select(Profile)
        .options(selectinload(Profile.user))
        .options(selectinload(Profile.skills))
        .where(Profile.id == updated_profile.id)
    )
    result = await session.exec(statement)
    profile_with_user = result.first()

    skills_response = []
    if profile_with_user.skills:
        for profile_skill in profile_with_user.skills:
            if profile_skill.skill:
                skills_response.append(
                    SkillDataResponse(
                        id=str(profile_skill.skill.id),
                        name=profile_skill.skill.name,
                        description=profile_skill.description,
                    )
                )

    return profile_response(
        "Profile updated successfully", profile_with_user, skills_response
    )


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
    responses=DELETE_AVATAR_RESPONSES,
)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete user's avatar"""
    profile = await profile_service.get_profile_by_user_id(
        str(current_user.id), session
    )

    # Delete from Cloudinary
    public_id = cloudinary_service.extract_public_id_from_url(profile.avatar_url)
    if public_id:
        await cloudinary_service.delete_image(public_id)

    # Reset to default avatar
    profile.avatar_url = None
    session.add(profile)
    await session.commit()

    return None


@router.get(
    "/{username}", response_model=ProfileResponse, responses=GET_USER_PROFILE_RESPONSES
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

    if not profile:  # same as if profile is None
        raise NotFound("Profile for user '{username}' not found")

    statement = (
        select(User)
        .options(
            selectinload(User.profile)
            .selectinload(Profile.skills)
            .selectinload(ProfileSkill.skill)
        )
        .where(User.id == profile.user_id)
    )

    result = await session.exec(statement)
    user = result.first()

    profile = user.profile

    skills_response = []

    if profile.skills:
        for profile_skill in profile.skills:
            if profile_skill.skill:
                skills_response.append(
                    SkillDataResponse(
                        id=str(profile_skill.skill.id),
                        name=profile_skill.skill.name,
                        description=profile_skill.description,
                    )
                )

    return profile_response("Profile retrieved successfully", profile, skills_response)


@router.post(
    "/me/skills",
    responses=ADD_SKILL_RESPONSES,
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_skill_to_profile(
    skill_data: SkillCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Add a new skill to user's profile

    EXAMPLE:
    - POST /profiles/me/skills with {"name": "Python", "description": "5 years"}
    - Creates link between johndoe and Python skill
    """

    profile = await profile_service.get_profile_by_user_id(current_user.id, session)

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
            created_at=profile_skill.skill.created_at,
        ),
    )


@router.get(
    "/{username}/skills",
    responses=GET_USER_SKILLS_RESPONSES,
    response_model=SkillListResponse,
)
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
        raise NotFound(f"Profile for user '{username}' not found")

    skills = await profile_service.get_profile_skills(str(profile.id), session)

    return SkillListResponse(
        status=SUCCESS_EXAMPLE,
        message="Skills retrieved successfully",
        data=[
            SkillDataResponse(
                id=str(skill.id),
                name=skill.skill.name,
                description=skill.description,
            )
            for skill in skills
        ],
    )


@router.patch(
    "/me/skills/{skill_id}",
    responses=UPDATE_SKILL_RESPONSES,
    response_model=SkillResponse,
)
async def update_skill(
    skill_id: UUID,
    skill_data: SkillUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update a specific skill in user's profile

    EXAMPLE:
    - PATCH /profiles/me/skills/123 with {"description": "10 years"}
    - Updates description of skill 123 in current profile
    """

    profile = await profile_service.get_profile_by_user_id(current_user.id, session)

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
            created_at=updated_skill.skill.created_at,
        ),
    )


@router.delete(
    "/me/skills/{skill_id}",
    responses=DELETE_SKILL_RESPONSES,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_skill(
    skill_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Remove a skill from user's profile

    NOTE: This only removes the link, not the skill itself
    - Skill still exists in Skills table
    - Other users can still have this skill

    EXAMPLE:
    - DELETE /profiles/me/skills/123
    - Removes skill 123 from current profile
    """

    profile = await profile_service.get_profile_by_user_id(current_user.id, session)

    profile_skill = await profile_service.get_profile_skill(
        skill_id=skill_id, profile_id=str(profile.id), session=session
    )

    if not profile_skill:
        raise NotFound("Skill not found in profile")

    await profile_service.delete_profile_skill(profile_skill, session)

    return None
