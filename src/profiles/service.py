from typing import List, Optional

from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.cloudinary_service import CloudinaryService
from src.db.models import Profile, ProfileSkill, Skill, User


class ProfileService:
    async def get_all_profiles(
        self,
        session: AsyncSession,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,  # e.g if 20, skip first 20
    ) -> List[Profile]:
        """
        Get list of all profiles with optional search
        """
        statement = select(Profile).join(User)

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    User.username.ilike(pattern),  # Search username
                    Profile.short_intro.ilike(pattern),  # Search intro
                    Profile.location.ilike(pattern),  # Search location
                )
            )

        statement = statement.offset(offset).limit(limit)

        result = await session.exec(statement)
        return result.all()

    async def get_profile_by_username(
        self, username: str, session: AsyncSession
    ) -> Optional[Profile]:
        """
        Get a profile by username
        """
        user_statement = select(User).where(User.username == username)
        user_result = await session.exec(user_statement)
        user = user_result.first()

        if not user:
            return None

        profile_statement = select(Profile).where(Profile.user_id == user.id)
        profile_result = await session.exec(profile_statement)
        return profile_result.first()

    async def get_profile_by_user_id(self, user_id: str, session: AsyncSession):
        """Get user profile by user_id"""
        statement = select(Profile).where(Profile.user_id == user_id)
        result = await session.exec(statement)
        return result.first()

    async def update_profile(
        self, profile: Profile, update_data: dict, session: AsyncSession
    ):
        """Update profile with new data"""
        for key, value in update_data.items():
            if value is not None:
                setattr(profile, key, value)

        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile

    async def update_avatar(
        self, profile: Profile, new_avatar_url: str, session: AsyncSession
    ):
        """Update profile avatar URL"""
        # Delete old avatar from Cloudinary if it's not the default
        default_avatar = "https://res.cloudinary.com/dq0ow9lxw/image/upload/v1732236186/default-image_foxagq.jpg"
        if profile.avatar_url != default_avatar:
            old_public_id = CloudinaryService.extract_public_id_from_url(
                profile.avatar_url
            )
            if old_public_id:
                await CloudinaryService.delete_image(old_public_id)

        # Update with new avatar URL
        profile.avatar_url = new_avatar_url
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile

    async def get_or_create_skill(
        self, skill_name: str, session: AsyncSession
    ) -> Skill:
        """
        Get existing skill or create new one
        """
        statement = select(Skill).where(Skill.name.ilike(skill_name))
        result = await session.exec(statement)
        skill = result.first()

        if skill:
            return skill

        new_skill = Skill(name=skill_name.title())
        session.add(new_skill)
        await session.commit()
        await session.refresh(new_skill)
        return new_skill

    async def add_skill_to_profile(
        self,
        profile_id: str,
        skill_name: str,
        description: Optional[str],
        session: AsyncSession,
    ) -> ProfileSkill:
        """
        Add a skill to user's profile
        """
        skill = await self.get_or_create_skill(skill_name, session)

        existing = await session.exec(
            select(ProfileSkill).where(
                ProfileSkill.profile_id == profile_id, ProfileSkill.skill_id == skill.id
            )
        )
        if existing.first():
            raise ValueError("Skill already exists in profile")

        profile_skill = ProfileSkill(
            profile_id=profile_id, skill_id=skill.id, description=description
        )
        session.add(profile_skill)
        await session.commit()
        await session.refresh(profile_skill)
        return profile_skill

    async def get_profile_skills(
        self, profile_id: str, session: AsyncSession
    ) -> List[ProfileSkill]:
        """Get all skills for a profile"""
        statement = select(ProfileSkill).where(ProfileSkill.profile_id == profile_id)
        result = await session.exec(statement)
        return result.all()

    async def get_profile_skill(
        self, skill_id: str, profile_id: str, session: AsyncSession
    ) -> Optional[ProfileSkill]:
        """Get a specific skill from a profile"""
        statement = select(ProfileSkill).where(
            ProfileSkill.skill_id == skill_id, ProfileSkill.profile_id == profile_id
        )
        result = await session.exec(statement)
        return result.first()

    async def update_profile_skill(
        self, profile_skill: ProfileSkill, update_data: dict, session: AsyncSession
    ) -> ProfileSkill:
        """
        Update a skill's information
        """
        # If updating skill name, we need to handle it specially
        if "name" in update_data and update_data["name"]:
            new_skill = await self.get_or_create_skill(update_data["name"], session)
            profile_skill.skill_id = new_skill.id

        if "description" in update_data:
            profile_skill.description = update_data["description"]

        session.add(profile_skill)
        await session.commit()
        await session.refresh(profile_skill)
        return profile_skill

    async def delete_profile_skill(
        self, profile_skill: ProfileSkill, session: AsyncSession
    ) -> None:
        """Remove a skill from profile"""
        await session.delete(profile_skill)
        await session.commit()


# TODO: FULL-TEXT SEARCH WITH POSTGRES
# 5) Full-text search (Postgres) - better performance for larger text fields
# from sqlalchemy import func
# ts_vector = func.to_tsvector('english', Profile.short_intro + ' ' + Profile.location + ' ' + User.username)
# stmt = select(Profile).join(User).where(ts_vector.match(search)).offset(offset).limit(limit)
# res = await session.exec(stmt)
# return res.all()
# NOTE: requires Postgres and proper indexes (GIN on to_tsvector).
