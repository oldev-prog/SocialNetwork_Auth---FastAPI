from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from app.data.models import AccountStatus

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8)

class RegisterRequest(LoginRequest):

    @field_validator('password')
    @classmethod
    def passw_strength(cls, password: str) -> str:
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r"[A-Z]", password):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, one number')
        if not re.search(r"[a-z]", password):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", password):
            print(password)
            raise ValueError('Password must contain at least one digit')
        if not re.search(r"[_!@#$%^&*(),.?\":{}|<>]", password):
            raise ValueError('Password must contain at least one special character')
        print(password)
        return password


class EmailOnlyRequest(BaseModel):
    email: EmailStr
