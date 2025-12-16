from datetime import datetime

from fastapi import File
from pydantic import BaseModel, ConfigDict, Field

from src.constants import VoteType


class TagResponseData(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagResponse(BaseModel):
    status: str
    message: str
    data: TagResponseData


class TagListResponse(BaseModel):
    status: str
    message: str
    data: list[TagResponseData]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str
    featured_image: str | None = None
    source_link: str | None = Field(default=None, max_length=200)
    demo_link: str | None = Field(default=None, max_length=200)


class ProjectUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    featured_image: str | None = None
    source_link: str = Field(default=None, max_length=200)
    demo_link: str = Field(default=None, max_length=200)


class ProjectOwnerInfo(BaseModel):
    user_id: str
    username: str
    full_name: str
    avatar_url: str | None = None


class ProjectResponseData(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    featured_image: str
    source_link: str | None = None
    demo_link: str | None = None
    vote_total: int
    vote_ratio: int
    created_at: datetime
    updated_at: datetime
    owner: ProjectOwnerInfo
    tags: list[TagResponse] = []
    reviews: list["ReviewResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    status: str
    message: str
    data: ProjectResponseData


class ProjectListResponseData(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    featured_image: str
    vote_total: int
    vote_ratio: int
    owner: ProjectOwnerInfo
    tags: list[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """
    Simplified project info for listing
    """

    status: str
    message: str
    data: list[ProjectListResponseData]


class ReviewCreate(BaseModel):
    value: VoteType
    content: str = Field(min_length=1, max_length=1000)


class ReviewResponseData(BaseModel):
    id: str
    value: VoteType
    content: str
    created_at: datetime
    reviewer: ProjectOwnerInfo  # Who left the review

    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(BaseModel):
    status: str
    message: str
    data: list[ReviewResponseData]


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
