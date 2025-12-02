from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from src.db.models import Profile
from src.cloudinary_service import CloudinaryService



class ProfileService:
    async def get_profile_by_user_id(self, user_id: str, session: AsyncSession):
        """Get user profile by user_id"""
        statement = select(Profile).where(Profile.user_id == user_id)
        result = await session.exec(statement)
        return result.first()
    
    async def update_profile(
        self, 
        profile: Profile, 
        update_data: dict, 
        session: AsyncSession
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
        self,
        profile: Profile,
        new_avatar_url: str,
        session: AsyncSession
    ):
        """Update profile avatar URL"""
        # Delete old avatar from Cloudinary if it's not the default
        default_avatar = "https://res.cloudinary.com/dq0ow9lxw/image/upload/v1732236186/default-image_foxagq.jpg"
        if profile.avatar_url != default_avatar:
            old_public_id = CloudinaryService.extract_public_id_from_url(profile.avatar_url)
            if old_public_id:
                await CloudinaryService.delete_image(old_public_id)
        
        # Update with new avatar URL
        profile.avatar_url = new_avatar_url
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile