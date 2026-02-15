import hashlib
from app.data.models import User, EmailVerification
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# async def update_db(obj: list[User|EmailVerification]|User, db: AsyncSession):
#     db.add(obj)
#     await db.commit()
#     await db.refresh(obj)
#     return {'details':'database has been successfully updated'}

async def update_db(obj: list | Any, db: AsyncSession):
    try:
        if isinstance(obj, list):
            db.add_all(obj)
        else:
            db.add(obj)

        await db.commit()

        if not isinstance(obj, list):
            await db.refresh(obj)

        return {'details': 'database has been successfully updated'}
    except Exception as e:
        await db.rollback()
        raise e
