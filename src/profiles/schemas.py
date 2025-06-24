from pydantic import BaseModel, Field

from src.auth.schemas import UserResponse, UserUpdate


# profile_id will be a path param for the skill creation
class Skill(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = None


class SkillUpdate(BaseModel):
    name: str = Field(default=None, max_length=100)
    description: str | None = None


# profile_id will be a path param for the profile update
class ProfileBase(BaseModel):
    user: UserResponse
    short_intro: str = Field(default=None, max_length=200)
    bio: str | None = None
    location: str = Field(default=None, max_length=100)
    avatar_url: str

    github: str = Field(default=None, max_length=200)
    stack_overflow: str = Field(default=None, max_length=200)
    tw: str = Field(default=None, max_length=200)
    ln: str = Field(default=None, max_length=200)
    website: str = Field(default=None, max_length=200)

    skills: list[Skill] = []


class ProfileUpdate(BaseModel):
    user: UserUpdate
    short_intro: str = Field(default=None, max_length=200)
    bio: str | None = None
    location: str = Field(default=None, max_length=100)
    avatar_url: str

    github: str = Field(default=None, max_length=200)
    stack_overflow: str = Field(default=None, max_length=200)
    tw: str = Field(default=None, max_length=200)
    ln: str = Field(default=None, max_length=200)
    website: str = Field(default=None, max_length=200)


class ProfileResponse(ProfileBase):
    pass
