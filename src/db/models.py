import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import EmailStr, model_validator
from slugify import slugify
from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlmodel import Column, Field, Relationship, SQLModel

from src.config import Config
from src.constants import UserRole, VoteType


def get_utc_now():
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    username: str = Field(sa_column=Column(String(50), nullable=False, unique=True))
    email: EmailStr = Field(sa_column=Column(String(50), nullable=False, unique=True))
    hashed_password: str = Field(exclude=True)
    is_active: bool = True
    is_email_verified: bool = False
    role: UserRole = Field(default=UserRole.user)

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
    )
    jwts: list["OutstandingToken"] | None = Relationship(
        back_populates="user", passive_deletes="all"
    )
    otps: list["Otp"] | None = Relationship(
        back_populates="user", passive_deletes="all"
    )
    profile: "Profile" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return self.full_name


class OutstandingToken(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="CASCADE"
    )
    user: User | None = Relationship(back_populates="jwts")
    jti: str = Field(unique=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    expires_at: datetime
    blacklisted_tokens: list["BlacklistedToken"] | None = Relationship(
        back_populates="token", passive_deletes="all"
    )
    

    def __repr__(self):
        return f"Refresh JTI: {self.jti}"

class BlacklistedToken(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    token_id: uuid.UUID | None = Field(
        default=None, foreign_key="outstandingtoken.id", ondelete="CASCADE"
    )
    token: OutstandingToken | None = Relationship(back_populates="blacklisted_tokens")
    
class Otp(SQLModel, table=True):
    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=True))
    otp: int
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    

    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="CASCADE"
    )
    user: User | None = Relationship(back_populates="otps")

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
    name: str = Field(max_length=100, unique=True)
    profile_skill: "ProfileSkill" = Relationship(
        back_populates="skill",
        passive_deletes="all",
    )

    def __repr__(self):
        return self.name


class ProfileSkill(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    description: str | None = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
    )
    profile_id: uuid.UUID | None = Field(
        default=None, foreign_key="profile.id", ondelete="CASCADE"
    )
    profile: Optional["Profile"] = Relationship(back_populates="skills")
    skill_id: uuid.UUID | None = Field(
        default=None, foreign_key="skill.id", ondelete="CASCADE"
    )
    skill: Skill | None = Relationship(back_populates="profile_skill")


class Profile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", unique=True, ondelete="CASCADE"
    )
    user: User | None = Relationship(back_populates="profile")
    short_intro: str | None = Field(default=None, max_length=200)
    bio: str | None = None
    location: str | None = Field(default=None, max_length=100)
    avatar_url: str = Field(
        default="https://res.cloudinary.com/dq0ow9lxw/image/upload/v1732236186/default-image_foxagq.jpg",
        max_length=200,
    )  # TODO: have to upload to cloudinary
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
    )

    # Social Links
    github: str | None = Field(default=None, max_length=200, nullable=True)
    stack_overflow: str | None = Field(default=None, max_length=200, nullable=True)
    tw: str | None = Field(default=None, max_length=200, nullable=True)
    ln: str | None = Field(default=None, max_length=200, nullable=True)
    website: str | None = Field(default=None, max_length=200, nullable=True)

    skills: list[ProfileSkill] | None = Relationship(
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

    def __repr__(self):
        return self.user.full_name


class Message(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    recipient_id: uuid.UUID | None = Field(
        default=None, foreign_key="profile.id", ondelete="CASCADE"
    )
    recipient: Profile | None = Relationship(back_populates="messages")
    name: str = Field(max_length=200)
    email: EmailStr = Field(max_length=50)
    subject: str = Field(max_length=200)
    body: str
    is_read: bool = False

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )

    def __repr__(self):
        return self.subject


class Tag(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    name: str = Field(max_length=50)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )

    projects: list["Project"] | None = Relationship(back_populates="tags")
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="project.id", ondelete="CASCADE"
    )


class Project(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    title: str = Field(index=True, max_length=255)

    slug: str = Field(default_factory=lambda self: slugify(self.title))
    owner: Profile | None = Relationship(back_populates="projects")
    owner_id: uuid.UUID | None = Field(
        default=None, foreign_key="profile.id", ondelete="CASCADE"
    )
    featured_image: str
    description: str = Field(index=True)
    source_link: str | None = Field(default=None, max_length=200)
    demo_link: str | None = Field(default=None, max_length=200)
    vote_total: int = Field(default=0)
    vote_ratio: int = Field(default=0)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
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
    project: Project | None = Relationship(back_populates="reviews")
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="project.id", ondelete="CASCADE"
    )
    profile: Profile | None = Relationship(back_populates="reviews")
    profile_id: uuid.UUID | None = Field(
        default=None, foreign_key="profile.id", ondelete="CASCADE"
    )
    value: VoteType
    content: str
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
