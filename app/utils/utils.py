import hashlib
from app.data.models import User, EmailVerification
from sqlalchemy.ext.asyncio import AsyncSession

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def update_db(obj: list[User|EmailVerification]|User, db: AsyncSession):
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return {'details':'database has been successfully updated'}
