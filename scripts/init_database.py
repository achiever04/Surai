"""
Initialize PostgreSQL database schema
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from config.settings import settings
from app.db.base import Base

# Import all models to register them
from app.models.user import User
from app.models.camera import Camera
from app.models.detection import Detection
from app.models.watchlist import WatchlistPerson
from app.models.evidence import Evidence
from app.models.blockchain_receipt import BlockchainReceipt

async def init_db():
    print("Initializing database...")
    
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    async with engine.begin() as conn:
        # Drop all tables (use carefully!)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())