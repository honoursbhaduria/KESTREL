"""Global test fixtures for Haron backend API.
Configures test database, async HTTP client, and mock/worker fixtures.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Set test environment before importing application modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://haron:haron_secret@localhost:5436/haron_test"
os.environ["REDIS_URL"] = "redis://localhost:6382/1"
os.environ["JWT_SECRET_KEY"] = "test_super_secret_jwt_key_that_is_at_least_32_chars_long"

from app.core.config import get_settings

get_settings.cache_clear()
test_settings = get_settings()

import app.ai.models  # noqa: F401
import app.db.session as db_session_module
import app.modules.assistant.models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.jobs.models  # noqa: F401
import app.modules.plans.models  # noqa: F401
import app.modules.projects.models  # noqa: F401
import app.modules.rules.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app

test_engine = create_async_engine(test_settings.DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

# Override the app's async_session_factory as well so background tasks in workers use the test DB
db_session_module.async_session_factory = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables in the test database once before the test session and tear down after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per test function."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client connected to the FastAPI app with test db override."""

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_org_a(client: AsyncClient) -> dict:
    """Register and return auth credentials + headers for User/Org A."""
    payload = {
        "email": f"architect_a_{os.urandom(4).hex()}@studio-alpha.com",
        "password": "Password123!Secure",
        "full_name": "Architect Alpha",
        "org_name": "Studio Alpha",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, f"Register A failed: {resp.text}"
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
        "org": data["org"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture
async def auth_org_b(client: AsyncClient) -> dict:
    """Register and return auth credentials + headers for User/Org B."""
    payload = {
        "email": f"architect_b_{os.urandom(4).hex()}@studio-beta.com",
        "password": "Password123!Secure",
        "full_name": "Architect Beta",
        "org_name": "Studio Beta",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, f"Register B failed: {resp.text}"
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
        "org": data["org"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }
