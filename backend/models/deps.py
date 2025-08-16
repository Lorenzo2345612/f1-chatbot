from models.db import async_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
