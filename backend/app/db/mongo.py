from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.api_key import APIKey
from app.models.token import RefreshToken
from app.models.user import User

_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGO_URL)
    await init_beanie(
        database=_client[settings.MONGO_DB],
        document_models=[User, APIKey, RefreshToken],
    )
    print(f"[DB] Connected to MongoDB: {settings.MONGO_DB}")


async def close_db() -> None:
    if _client:
        _client.close()
        print("[DB] MongoDB connection closed")


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Database not initialised. Call connect_db() first.")
    return _client
