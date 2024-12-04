from typing import List, Optional
from pydantic import EmailStr
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import SQLModel, Field, Column, Relationship
from datetime import datetime, date
from slugify import slugify
import uuid
import pyotp

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    username: str = Field(default="", nullable=False)
    email: EmailStr
    first_name: str
    last_name: str
    is_verified: bool = False
    is_active: bool = True
    password_hash: str = Field(exclude=True)
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now, index=True))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    
    def generate_slug(self):
        self.username = slugify(f"{self.first_name}-{self.last_name}")
        
    def __repr__(self):
        return f'<User {self.username}>'
    
class Otp(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user: str = Relationship(
        back_populates='otp'
    )
    otp: int
    created_at: datetime = Field(default=datetime.now)