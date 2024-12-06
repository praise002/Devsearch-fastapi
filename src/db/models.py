from typing import List, Optional
from pydantic import EmailStr
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import SQLModel, Field, Column, Relationship
from datetime import datetime, timedelta
from slugify import slugify
import uuid

from src.config import Settings

s = Settings()

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4,
            index=True,
        )
    )
    username: str = Field(default="", nullable=False)
    email: EmailStr
    first_name: str
    last_name: str
    is_verified: bool = False
    is_active: bool = True
    password_hash: str = Field(exclude=True) # prevents it from being included in serialized outputs
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now, index=True))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    otps: List["Otp"] = Relationship(back_populates="user")  # Establish relationship
    
    def generate_slug(self):
        self.username = slugify(f"{self.first_name}-{self.last_name}")
        
    def __repr__(self): # Provides a developer-friendly string representation of a User instance
        return f'<User {self.username}>'


class Otp(SQLModel, table=True):
    id: int = Field(
        primary_key=True,
        sa_column=Column(pg.INTEGER, autoincrement=True),
        index=True,
    )
    user_uid: uuid.UUID = Field(nullable=False, foreign_key='users.uid')
    otp: int 
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    user: Optional[User] = Relationship(back_populates="otps")  # Establish relationship
    
    @property
    def is_valid(self) -> bool:
        """
        Check if the OTP is still valid based on expiration settings.
        """
        expiration_time = self.created_at + timedelta(minutes=s.EMAIL_OTP_EXPIRE_MINUTES)
        return datetime.now() < expiration_time
    
    def __repr__(self): 
        return f'<Otp {self.otp}>'
