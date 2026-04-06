"""
Database initialization utilities
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from loguru import logger


async def init_db():
    """Initialize database with default data"""
    async with AsyncSessionLocal() as session:
        try:
            await create_default_admin(session)
            await session.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error initializing database: {e}")
            raise


async def create_default_admin(session: AsyncSession):
    """Create default admin user if not exists"""
    # Check if admin exists
    result = await session.execute(
        select(User).where(User.username == "admin")
    )
    existing_admin = result.scalar_one_or_none()
    
    if existing_admin:
        logger.info("Admin user already exists")
        return
    
    # Create admin
    admin = User(
        username="admin",
        email="admin@surveillance.local",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),
        role="admin",
        is_active=True,
        is_superuser=True
    )
    
    session.add(admin)
    logger.info("Default admin user created (username: admin, password: admin123)")


async def create_sample_data(session: AsyncSession):
    """Create sample data for development/testing"""
    from app.models.camera import Camera
    
    # Check if cameras exist
    result = await session.execute(select(Camera))
    if result.scalar_one_or_none():
        logger.info("Sample data already exists")
        return
    
    # Create sample camera
    sample_camera = Camera(
        name="Demo Camera",
        source_type="webcam",
        source_url="0",
        location="Main Entrance",
        resolution_width=1280,
        resolution_height=720,
        fps=10,
        is_active=False
    )
    
    session.add(sample_camera)
    logger.info("Sample camera created")


async def reset_database():
    """WARNING: Reset entire database (development only)"""
    from app.db.base import Base
    from app.db.session import engine
    
    logger.warning("Resetting database - all data will be lost!")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database reset complete")
    
    # Reinitialize with defaults
    await init_db()


if __name__ == "__main__":
    asyncio.run(init_db())