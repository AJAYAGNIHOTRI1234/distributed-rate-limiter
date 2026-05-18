from fastapi import APIRouter

from app.db.mongo import get_client
from app.db.redis_client import get_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    redis_ok = False
    try:
        r = get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    mongo_ok = False
    try:
        client = get_client()
        await client.admin.command("ping")
        mongo_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if (redis_ok and mongo_ok) else "degraded",
        "redis": "ok" if redis_ok else "unreachable",
        "mongodb": "ok" if mongo_ok else "unreachable",
    }
