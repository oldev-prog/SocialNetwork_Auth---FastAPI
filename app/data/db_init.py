from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.data.config import settings
from app.data.class_base import Base

async_engine = create_async_engine(
    url=settings.DATABASE_async_url,
    echo=True)

async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)

async def setup_db():
    async with async_engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)

        await conn.commit()

