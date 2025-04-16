from pydantic import BaseModel, EmailStr

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str = "OK"

class TokenData(BaseModel):
    email: EmailStr | None = None
    user_id: int | None = None
    user_type_id: int | None = None 