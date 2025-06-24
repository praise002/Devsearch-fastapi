from pydantic import BaseModel, EmailStr, Field


class MessageCreate(BaseModel):
    name: str = Field(max_length=200)
    email: EmailStr
    subject: str = Field(max_length=200)
    body: str