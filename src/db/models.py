import uuid
from datetime import datetime, timedelta, timezone

from pydantic import EmailStr, model_validator
from slugify import slugify
from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlmodel import Column, Field, Relationship, SQLModel

from src.config import Config
from src.constants import UserRole, VoteType


def get_utc_now():
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    username: str = Field(sa_column=Column(String(50), nullable=False, unique=True))
    email: EmailStr = Field(sa_column=Column(String(50), nullable=False, unique=True))
    hashed_password: str = Field(exclude=True)
    is_active: bool = True
    is_email_verified: bool = False
    role: UserRole = Field(default=UserRole.user)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=get_utc_now,
            onupdate=get_utc_now,
            nullable=False,
        )
    )
    otps: list["Otp"] | None = Relationship(
        back_populates="user", passive_deletes="all"
    )
    profile: "Profile" = Relationship(back_populates="user", passive_deletes="all")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class Otp(SQLModel, table=True):
    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    otp: int
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="otps")

    @model_validator(mode="after")
    @property
    def is_valid(self) -> bool:
        """
        Check if the OTP is still valid based on expiration settings.
        """
        expiration_time = self.created_at + timedelta(
            minutes=Config.EMAIL_OTP_EXPIRE_MINUTES
        )
        return timezone.now() < expiration_time

    def __str__(self):
        return self.otp


class Skill(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    description: str | None = None
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )

    profile_id: uuid.UUID = Field(foreign_key="profile.id", ondelete="CASCADE")
    profile: "Profile" = Relationship(back_populates="skills")

    def __str__(self):
        return self.name


class Profile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="profile")
    short_intro: str = Field(default=None, max_length=200)
    bio: str | None = None
    location: str = Field(default=None, max_length=100)
    avatar_url: str = Field(
        default="https://res.cloudinary.com/dq0ow9lxw/image/upload/v1732236186/default-image_foxagq.jpg"
    )  # TODO: have to upload to cloudinary
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=get_utc_now,
            onupdate=get_utc_now,
            nullable=False,
        )
    )

    # Social Links
    github: str = Field(default=None, max_length=200, nullable=True)
    stack_overflow: str = Field(default=None, max_length=200, nullable=True)
    tw: str = Field(default=None, max_length=200, nullable=True)
    ln: str = Field(default=None, max_length=200, nullable=True)
    website: str = Field(default=None, max_length=200, nullable=True)

    skills: list[Skill] | None = Relationship(
        back_populates="profile", passive_deletes="all"
    )

    reviews: list["Review"] | None = Relationship(
        back_populates="profile", passive_deletes="all"
    )

    messages: list["Message"] | None = Relationship(
        back_populates="recipient", passive_deletes="all"
    )

    projects: list["Project"] | None = Relationship(
        back_populates="owner", passive_deletes="all"
    )

    def __str__(self):
        return self.user.full_name


class Message(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    recipient_id: uuid.UUID = Field(foreign_key="profile.id", ondelete="CASCADE")
    recipient: Profile = Relationship(back_populates="messages")
    name: str = Field(max_length=200)
    email: EmailStr = Field(max_length=50)
    subject: str = Field(max_length=200)
    body: str
    is_read: bool = False

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )

    def __str__(self):
        return self.subject


class Tag(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    name: str = Field(max_length=50)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )

    projects: list["Project"] | None = Relationship(back_populates="tags")
    project_id: uuid.UUID = Field(foreign_key="project.id", ondelete="CASCADE")


class Project(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    title: str = Field(index=True, max_length=255)

    slug: str = Field(default_factory=lambda self: slugify(self.title))
    owner: Profile = Relationship(back_populates="projects")
    owner_id: uuid.UUID = Field(foreign_key="profile.id", ondelete="CASCADE")
    featured_image: str
    description: str = Field(index=True)
    source_link: str = Field(default=None, max_length=200)
    demo_link: str = Field(default=None, max_length=200)
    vote_total: int = Field(default=0)
    vote_ratio: int = Field(default=0)
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=get_utc_now,
            onupdate=get_utc_now,
            nullable=False,
        )
    )

    tags: list[Tag] | None = Relationship(
        back_populates="projects", passive_deletes="all"
    )
    reviews: list["Review"] | None = Relationship(
        back_populates="project", passive_deletes="all"
    )


class Review(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("profile_id", "project_id", name="uq_profile_project_review"),
    )

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    project: Project = Relationship(back_populates="reviews")
    project_id: uuid.UUID = Field(foreign_key="project.id", ondelete="CASCADE")
    profile: Profile = Relationship(back_populates="reviews")
    profile_id: uuid.UUID = Field(foreign_key="profile.id", ondelete="CASCADE")
    value: VoteType
    content: str
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
        )
    )
