from app.data.models import User, AccountStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, email: str, password_hash: str, account_status: AccountStatus) -> User:
        new_user = User(
            email=email,
            password_hash=password_hash,
            account_status=account_status,
        )

        try:
            logger.debug(f'Connecting to database')
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            logger.info(f'User created: {new_user.email}')
        except Exception as e:
            logger.error('Error creating user: s%', e)

        return new_user

    async def get_user(self, email: str) -> User|None:
        try:
            logger.debug(f'Connecting to database')
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
        except Exception as e:
            logger.error('Error getting user: s%', e)
            return None

        user = result.scalar_one_or_none()

        if user:
            logger.info(f'User found: {user.email}')
        else:
            logger.info(f'User with email {email} not found (it is good for signup)')
            return None

        return user

