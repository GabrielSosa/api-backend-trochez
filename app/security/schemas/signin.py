from pydantic import BaseModel, EmailStr

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    message: str

class TokenData(BaseModel):
    email: str | None = None
    user_id: int | None = None 