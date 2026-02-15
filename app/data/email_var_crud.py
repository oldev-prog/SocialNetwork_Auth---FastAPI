from app.data.models import EmailVerification
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class EmailVarCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_var_token(self, user_email: str, hashed_token: str, ) -> EmailVerification:


        new_token = EmailVerification(
        user_email=user_email,
        hashed_token=hashed_token,
        expires_at=datetime.now(timezone.utc)+timedelta(hours=24)
        )

        try:
            logger.debug('Connecting to database')
            self.db.add(new_token)
            await self.db.commit()
            await self.db.refresh(new_token)
            logger.info('Successfully added new token: %s', new_token)
        except Exception as e:
            raise

        return new_token


    async def check_exist_token(self, hash: str) -> EmailVerification|None:
        try:
            logger.debug('Connecting to database')
            result = await self.db.execute(
                select(EmailVerification).where(EmailVerification.hashed_token == hash)
            )
        except Exception as e:
            logger.exception('Failed to check existing token: %s', e)
            raise

        token = result.scalar_one_or_none()
        logger.info('Successfully found existing token: %s', token)
        if not token:
            return None

        return token

