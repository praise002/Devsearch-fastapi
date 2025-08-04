from typing import Self

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    username: str  # NOTE: SHOULD NEVER CHANGE and be unique
    email: EmailStr

    @model_validator(mode="after")
    def validate(self) -> Self:
        if len(self.first_name.split()) > 1 or len(self.last_name.split()) > 1:
            raise ValueError("No spacing allowed")

        return self


class UserInDB(UserBase):
    hashed_password: str


class UserCreate(UserBase):
    password: str | None = None


class OtpVerify(BaseModel):
    email: EmailStr
    otp: int

    @field_validator("otp", mode="after")
    @classmethod
    def check_otp_digits(cls, value: int) -> str:
        if not (100000 <= value <= 999999):
            raise ValueError("OTP must be a 6-digit number")
        return value


class SendOtp(BaseModel):
    email: EmailStr


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)


class UserResponse(BaseModel):
    email: EmailStr
    message: str = "Account Created! Check email to verify your account"


class UserLoginModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class PasswordResetModel(BaseModel):
    email: EmailStr


class PasswordResetVerifyOtpModel(BaseModel):
    email: EmailStr
    otp: int


class PasswordResetConfirmModel(BaseModel):
    email: EmailStr
    new_password: str
    confirm_new_password: str

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Password does not match")
        return self


class PasswordChangeModel(BaseModel):
    old_password: str
    new_password: str
    confirm_new_password: str

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Password does not match")
        return self
