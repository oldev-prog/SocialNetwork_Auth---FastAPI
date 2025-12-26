from pydantic import BaseModel, EmailStr, Field
from app.data.models import AccountStatus

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8)

class RegisterRequest(LoginRequest):
    pass
