import re
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserBase(BaseModel):
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    username: str  # NOTE: SHOULD NEVER CHANGE and be unique
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def validate(self) -> Self:
        if len(self.first_name.split()) > 1 or len(self.last_name.split()) > 1:
            raise ValueError("No spacing allowed")

        return self


class UserInDB(UserBase):
    hashed_password: str


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=20)

    @field_validator("password", mode="after")
    @classmethod
    def validate_new_password(cls, value: str) -> str:

        if not re.match(
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()-+]).{8,}$",
            value,
        ):
            raise ValueError(
                "This password must contain at least 8 characters, one uppercase letter, one lowercase letter, one digit and one symbol."
            )
        # TODO: ADD MORE TO THE LIST
        if value.lower() in ["password", "123456789", "qwerty123", "admin123"]:
            raise ValueError("Password is too common. Choose a stronger password")

        return value


class UserCreateOAuth(UserBase):
    auth_provider: str | None = None
    google_id: str | None = None


class OtpVerify(BaseModel):
    email: EmailStr
    otp: int = Field(examples=[123456])

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("otp", mode="after")
    @classmethod
    def check_otp_digits(cls, value: int) -> str:
        if not (100000 <= value <= 999999):
            raise ValueError("OTP must be a 6-digit number")
        return value


class SendOtp(BaseModel):
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)


class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    # User fields
    id: UUID
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


class UserRegistrationResponse(BaseModel):
    status: str = "success"
    email: EmailStr
    message: str = "Account Created! Check email to verify your account"


class UserLoginModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class PasswordResetModel(BaseModel):
    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class PasswordResetVerifyOtpModel(BaseModel):
    email: EmailStr
    otp: int


class PasswordResetConfirmModel(BaseModel):
    email: EmailStr
    new_password: str
    confirm_new_password: str

    @field_validator("email", mode="after")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("new_password", mode="after")
    @classmethod
    def validate_new_password(cls, value: str) -> str:

        if not re.match(
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()-+]).{8,}$",
            value,
        ):
            raise ValueError(
                "This password must contain at least 8 characters, one uppercase letter, one lowercase letter, one digit and one symbol."
            )
        # TODO: ADD MORE TO THE LIST
        if value.lower() in ["password", "123456789", "qwerty123", "admin123"]:
            raise ValueError("Password is too common. Choose a stronger password")

        return value

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Password does not match")
        return self


class PasswordChangeModel(BaseModel):
    old_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password", mode="after")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not re.match(
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()-+]).{8,}$", value
        ):
            raise ValueError(
                "This password must contain at least 8 characters, one uppercase letter, one lowercase letter, one digit and one symbol."
            )
        # TODO: ADD MORE TO THE LIST
        if value.lower() in ["password", "123456789", "qwerty123", "admin123"]:
            raise ValueError("Password is too common. Choose a stronger password")

        return value

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Password does not match")
        return self

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Password does not match")
        return self
