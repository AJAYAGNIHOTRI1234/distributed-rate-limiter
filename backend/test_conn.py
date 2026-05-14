
import asyncio
import motor.motor_asyncio
import redis.asyncio as aioredis
from app.core.config import settings

async def test_conn():
    print(f"Testing MongoDB: {settings.MONGO_URL}")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
        await client.admin.command('ping')
        print("[SUCCESS] MongoDB Connected")
    except Exception as e:
        print(f"[FAILURE] MongoDB Failed: {e}")

    redis_url = settings.REDIS_URL.replace("localhost", "127.0.0.1")
    print(f"Testing Redis: {redis_url}")
    try:
        # Try without password first
        r = aioredis.from_url(redis_url, socket_timeout=5)
        await r.ping()
        print("[SUCCESS] Redis Connected (No password)")
    except Exception as e:
        print(f"[INFO] Redis No-password Failed: {e}")
        try:
            # Try with default password 'redispass'
            url_with_pass = redis_url.replace("redis://", "redis://:redispass@")
            print(f"Testing Redis with password: {url_with_pass}")
            r = aioredis.from_url(url_with_pass, socket_timeout=5)
            await r.ping()
            print("[SUCCESS] Redis Connected (With password 'redispass')")
        except Exception as e2:
            print(f"[FAILURE] Redis Authenticated Failed: {e2}")

if __name__ == "__main__":
    asyncio.run(test_conn())
