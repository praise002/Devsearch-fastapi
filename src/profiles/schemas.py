from pydantic import BaseModel, ConfigDict, EmailStr, Field


# profile_id will be a path param for the skill creation
class Skill(BaseModel):
    name: str = Field(max_length=100)
    description: str | None = None


class SkillUpdate(BaseModel):
    name: str = Field(default=None, max_length=100)
    description: str | None = None


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    short_intro: str = Field(default=None, max_length=200)
    bio: str | None = None
    location: str = Field(default=None, max_length=100)
    avatar_url: str

    github: str = Field(default=None, max_length=200)
    stack_overflow: str = Field(default=None, max_length=200)
    tw: str = Field(default=None, max_length=200)
    ln: str = Field(default=None, max_length=200)
    website: str = Field(default=None, max_length=200)


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileResponse(BaseModel):
    status: str
    message: str
    # User fields
    id: str
    first_name: str
    last_name: str
    username: str
    email: EmailStr

    # Profile fields
    short_intro: str | None = None
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = None
    github: str | None = None
    stack_overflow: str | None = None
    tw: str | None = None
    ln: str | None = None
    website: str | None = None

    skills: list[SkillResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AvatarUploadResponse(BaseModel):
    status: str = "success"
    message: str
    avatar_url: str
