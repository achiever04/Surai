"""
Database session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

engine_kwargs = {"echo": False, "future": True}
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10})

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create SYNC engine for background threads (detection processor)
# Convert async URL to sync URL
sync_db_url = settings.DATABASE_URL
if "postgresql+asyncpg" in sync_db_url:
    sync_db_url = sync_db_url.replace("postgresql+asyncpg://", "postgresql://")
elif "sqlite+aiosqlite" in sync_db_url:
    sync_db_url = sync_db_url.replace("sqlite+aiosqlite://", "sqlite://")

sync_engine_kwargs = {"echo": False}
if "sqlite" in sync_db_url:
    sync_engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    sync_engine_kwargs.update({"pool_pre_ping": True, "pool_size": 3, "max_overflow": 5})

sync_engine = create_engine(sync_db_url, **sync_engine_kwargs)

# Sync session factory for background threads
SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    """Dependency for getting database session (async)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_sync_db():
    """Get synchronous database session for background threads"""
    session = SyncSessionLocal()
    try:
        return session
    except Exception:
        session.rollback()
        session.close()
        raise