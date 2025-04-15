from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=45)
    code: str = Field(..., min_length=1, max_length=45)
    description: str = Field(..., min_length=1, max_length=100)
    pages: Optional[str] = Field(None, max_length=450)

class UserTypeCreate(UserTypeBase):
    pass

class UserTypeUpdate(UserTypeBase):
    name: Optional[str] = Field(None, min_length=1, max_length=45)
    code: Optional[str] = Field(None, min_length=1, max_length=45)
    description: Optional[str] = Field(None, min_length=1, max_length=100)

class UserTypeInDB(UserTypeBase):
    user_type_id: int
    created_date: datetime

    class Config:
        from_attributes = True 