from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import uuid
from datetime import datetime

class UserCreateModel(BaseModel):
    first_name: str = Field(max_length=25)
    last_name: str = Field(max_length=25)
    email: str = Field(max_length=40)
    password: str = Field(min_length=6)
    
    @model_validator(mode="before")
    def check_names(cls, values):
        first_name = values.get("first_name")
        last_name = values.get("last_name")
        
        if len(first_name.split()) > 1:
            raise ValueError("No spacing allowed")
        
        if len(last_name.split()) > 1:
            raise ValueError("No spacing allowed")
        
        return values
    
class UserModel(BaseModel):
    uid: uuid.UUID 
    username: str
    email: str
    first_name: str
    last_name: str
    is_verified: bool 
    is_active: bool 
    password_hash: str = Field(exclude=True)
    created_at: datetime 
    updated_at: datetime  
    
class UserLoginModel(BaseModel):
    email: EmailStr = Field(max_length=40)
    password: str = Field(min_length=6)
    
class PasswordResetModel(BaseModel):
    email: EmailStr
    
class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str
    
    @field_validator("confirm_new_password")
    def passwords_match(cls, value, values):
        if "new_password" in values and value != values["new_password"]:
            raise ValueError("Passwords do not match")
        return value

    
class PasswordChangeModel(BaseModel):
    old_password: str
    new_password: str
    confirm_new_password: str
    
    @field_validator("confirm_new_password")
    def passwords_match(cls, value, values):
        if "new_password" in values and value != values["new_password"]:
            raise ValueError("Passwords do not match")
        return value