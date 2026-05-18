import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.mongo import connect_db, close_db
from app.db.redis_client import init_redis, close_redis
from app.core.config import settings

# Set env vars BEFORE any imports that might use them (though app is already imported)
os.environ["JWT_SECRET"] = "test-secret-key-12345"
os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["MONGO_DB"] = "rateguard_test"

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Force test settings on the singleton
    settings.MONGO_DB = "rateguard_test"
    settings.JWT_SECRET = "test-secret-key-12345"
    settings.SECRET_KEY = "test-secret-key-12345"
    await connect_db()
    await init_redis()
    yield
    await close_db()
    await close_redis()

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
