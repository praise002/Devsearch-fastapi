from uuid import UUID

from pydantic import BaseModel, Field

from src.constants import VoteType


class Tag(BaseModel):
    name: str = Field(max_length=50)


class ProjectBase(BaseModel):
    title: str = Field(max_length=255)
    featured_image: str
    description: str
    source_link: str = Field(default=None, max_length=200)
    demo_link: str = Field(default=None, max_length=200)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: str = Field(default=None, max_length=255)
    featured_image: str | None = None
    description: str | None = None
    source_link: str = Field(default=None, max_length=200)
    demo_link: str = Field(default=None, max_length=200)


class ProjectResponse(ProjectBase):
    tags: list[Tag] | None = None
    reviews: list["Review"] | None = None


# project_id will be a path param, profile_id will be gotten from request
class Review(BaseModel):
    value: VoteType
    content: str
