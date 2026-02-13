from app.data.db_init import async_session_factory
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

async def get_db():
    async with async_session_factory() as session:
        yield session

db_session = Annotated[AsyncSession, Depends(get_db)]