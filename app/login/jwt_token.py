import jwt
import os
from datetime import datetime, timedelta, timezone
import bcrypt
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.data.models import RefreshToken
from app.data.config import settings
import uuid

logger = logging.getLogger(__name__)

class JWTTokenCRUD:
    def __init__(self, db: AsyncSession) -> None:
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM

        self.ACCESS_TOKEN_EXPIRE_MINUTES = 15
        self.REFRESH_TOKEN_EXPIRE_DAYS = 30

        self.db = db


    def create_access_token(self, user_id: int) -> (str, int):
        payload = {
            'sub': str(user_id),
            'scope': 'access',
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return token, self.ACCESS_TOKEN_EXPIRE_MINUTES


    def create_refresh_token(self, user_id: int) -> list[str]:
        session_id = str(uuid.uuid4())
        payload = {
            'sub': str(user_id),
            'scope': 'refresh',
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS),
            'jti': session_id
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return token, session_id


    async def add_refresh_token(self, token_hash: str, user_id: int, session_id: str) -> RefreshToken:

        new_refresh_token = RefreshToken(
        user_id=user_id,
        refresh_token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)+timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS),
        session_id=session_id

        )

        try:
            self.db.add(new_refresh_token)
            await self.db.commit()
            await self.db.refresh(new_refresh_token)
        except Exception as e:
            logger.error('Failed to add new refresh token: %s', e)

        return new_refresh_token

    async def set_refresh_token(self, user_id: int, hashed_token: str):
        query_delete = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        await self.db.execute(query_delete)

        await self.add_refresh_token(hashed_token, user_id)

    async def revoke_specific_token(self, user_id: int, session_id: str):
        query = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.session_id == session_id
        )
        await self.db.execute(query)


    async def get_refresh_token(self, user_id: int) -> RefreshToken|None:
        try:
            result = await self.db.execute(
                select(RefreshToken).where(RefreshToken.user_id == user_id)
            )
        except Exception as e:
            logger.error('Failed to get refresh token: %s', e)
            return None

        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            return None
        else:
            return refresh_token


    def decode_refresh_token(self, token: str) -> RefreshToken:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

        if payload['scope'] != 'refresh':
            raise Exception('Invalid refresh token scope')

        return payload