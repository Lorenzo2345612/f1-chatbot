from models.db import engine, Base

async def on_startup():
    async with engine.begin() as conn:
        # Remove all existing tables
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables defined in the Base metadata
        await conn.run_sync(Base.metadata.create_all)