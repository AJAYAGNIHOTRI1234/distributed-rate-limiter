import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis | None = None


async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    print("[Redis] Connected")


async def close_redis():
    if redis_client:
        await redis_client.aclose()


def get_redis() -> aioredis.Redis:
    return redis_client
