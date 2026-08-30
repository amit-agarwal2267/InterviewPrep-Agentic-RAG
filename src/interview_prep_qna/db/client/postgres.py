from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from interview_prep_qna.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if settings.database_host:
        database_url = URL.create(
            "postgresql+asyncpg",
            username=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            host=settings.database_host,
            port=5432,
            database=settings.postgres_db,
        )
    else:
        database_url = settings.database_url.get_secret_value()
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 3},
    )


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
