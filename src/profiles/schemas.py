from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from src.auth.schemas import SUCCESS_EXAMPLE


# profile_id will be a path param for the skill creation
class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(None, max_length=500)


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class SkillData(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillResponse(BaseModel):
    status: str
    message: str
    data: SkillData


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    short_intro: str = Field(default=None, max_length=200)
    bio: str | None = None
    location: str = Field(default=None, max_length=100)
    avatar_url: str | None = None

    github: str = Field(default=None, max_length=200)
    stack_overflow: str = Field(default=None, max_length=200)
    tw: str = Field(default=None, max_length=200)
    ln: str = Field(default=None, max_length=200)
    website: str = Field(default=None, max_length=200)


class SkillDataResponse(BaseModel):
    id: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SkillResponse(BaseModel):
    status: str
    message: str
    data: SkillDataResponse


class SkillListResponse(BaseModel):
    status: str
    message: str
    data: list[SkillDataResponse]


class ProfileData(BaseModel):
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

    skills: list[SkillDataResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProfileResponse(BaseModel):
    status: str
    message: str
    data: ProfileData


class ProfileListResult(BaseModel):
    id: str
    user_id: str
    username: str
    full_name: str
    short_intro: str | None = None
    location: str | None = None
    avatar_url: HttpUrl | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginationData(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[ProfileListResult]


class ProfileListResponse(BaseModel):
    status: str
    message: str
    data: PaginationData


class AvatarUploadResponse(BaseModel):
    status: str = SUCCESS_EXAMPLE
    message: str
    avatar_url: HttpUrl
