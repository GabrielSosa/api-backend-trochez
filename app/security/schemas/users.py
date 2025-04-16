from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    user_type_id: int
    name: str = Field(..., max_length=100)
    email: EmailStr
    profile_picture_url: Optional[str] = None
    change_pass: Optional[bool] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    profile_picture_url: Optional[str] = None
    change_pass: Optional[bool] = None

class UserInDB(UserBase):
    user_id: int
    created_date: datetime
    updated_date: Optional[datetime]

    class Config:
        from_attributes = True 