from pydantic import BaseModel
from enum import Enum
from typing import Optional

class TokenName(str, Enum):
    access_token = 'access_token'
    refresh_token = 'refresh_token'

class TokenType(str, Enum):
    bearer = 'bearer'

class AccessTokenResponse(BaseModel):
    access_token: TokenName
    token_type: TokenType
    expires_in: int
    details: Optional[dict]

class RefreshTokenResponse(BaseModel):
    details: Optional[dict]

class BaseResponse(BaseModel):
    details: dict

