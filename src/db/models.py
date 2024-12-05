from typing import List, Optional
from pydantic import EmailStr
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import SQLModel, Field, Column, Relationship
from datetime import datetime, date
from slugify import slugify
import uuid

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
    password_hash: str = Field(exclude=True) # prevents it from being included in serialized outputs
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now, index=True))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    
    def generate_slug(self):
        self.username = slugify(f"{self.first_name}-{self.last_name}")
        
    def __repr__(self): # Provides a developer-friendly string representation of a User instance
        return f'<User {self.username}>'
    
