"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from app.main import app
from app.db.base import Base
from app.core.security import get_password_hash
from app.models.user import User
from app.models.camera import Camera
from app.models.watchlist import WatchlistPerson
from config.settings import settings


# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.POSTGRES_DB,
    f"{settings.POSTGRES_DB}_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        role="operator",
        is_active=True
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user"""
    admin = User(
        username="testadmin",
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("adminpass123"),
        role="admin",
        is_active=True,
        is_superuser=True
    )
    
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    
    return admin


@pytest.fixture
async def auth_token(client: AsyncClient, test_user: User) -> str:
    """Get authentication token for test user"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": "testpass123"
        }
    )
    
    return response.json()["access_token"]


@pytest.fixture
async def admin_token(client: AsyncClient, test_admin: User) -> str:
    """Get authentication token for test admin"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_admin.username,
            "password": "adminpass123"
        }
    )
    
    return response.json()["access_token"]


@pytest.fixture
async def test_camera(db_session: AsyncSession) -> Camera:
    """Create test camera"""
    camera = Camera(
        name="Test Camera",
        source_type="webcam",
        source_url="0",
        location="Test Location",
        resolution_width=1280,
        resolution_height=720,
        fps=10,
        is_active=True
    )
    
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)
    
    return camera


@pytest.fixture
async def test_watchlist_person(db_session: AsyncSession) -> WatchlistPerson:
    """Create test watchlist person"""
    import numpy as np
    
    person = WatchlistPerson(
        person_id="TEST001",
        name="Test Person",
        category="person_of_interest",
        risk_level="medium",
        age=30,
        gender="male",
        face_embeddings=[np.random.randn(512).tolist()],
        photo_hashes=["test_hash_123"],
        num_photos=1,
        photos_local_paths=["/test/path/photo.jpg"],
        enrolled_by="test_system",
        alert_on_detection=True,
        is_active=True
    )
    
    db_session.add(person)
    await db_session.commit()
    await db_session.refresh(person)
    
    return person


@pytest.fixture
def sample_face_embedding():
    """Generate sample face embedding"""
    import numpy as np
    return np.random.randn(512).astype(np.float32)


@pytest.fixture
def sample_frame():
    """Generate sample video frame"""
    import numpy as np
    return np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def mock_ipfs_client(monkeypatch):
    """Mock IPFS client"""
    class MockIPFSClient:
        def add_bytes(self, data):
            return "QmTest123456789"
        
        def cat(self, cid):
            return b"test data"
        
        def pin(self):
            return self
        
        def add(self, cid):
            pass
    
    return MockIPFSClient()


@pytest.fixture
def mock_blockchain_service(monkeypatch):
    """Mock blockchain service"""
    class MockBlockchainService:
        async def register_evidence(self, *args, **kwargs):
            return "mock_tx_123"
        
        async def get_evidence_provenance(self, event_id):
            return {
                "event_id": event_id,
                "is_verified": True
            }
    
    return MockBlockchainService()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )