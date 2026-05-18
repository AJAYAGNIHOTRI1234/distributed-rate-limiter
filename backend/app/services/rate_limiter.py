import time
import uuid
import json
from app.core.config import settings
from app.core.security import verify_api_key
from app.db.redis_client import get_redis

LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local clear_before = now - window

-- Remove old elements
redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)

-- Count remaining elements
local current_requests = redis.call('ZCARD', key)

local allowed = 0
if current_requests < limit then
    -- Add the current request
    redis.call('ZADD', key, now, member)
    -- Set TTL on the key so it cleans up automatically
    redis.call('EXPIRE', key, window * 2)
    allowed = 1
    current_requests = current_requests + 1
end

return {allowed, limit - current_requests}
"""


async def get_key_metadata(plain_key: str) -> dict | None:
    """
    Validates the API key and returns cached or fetched metadata:
    {
        "id": "...",
        "key_hash": "...",
        "plan": "free",
        "is_active": true
    }
    Returns None if the key is invalid or not found.
    """
    if not plain_key or len(plain_key) < 16:
        return None

    prefix = plain_key[:16]
    cache_key = f"rateguard:key_cache:{prefix}"

    # 1. Try to read from Redis cache
    redis = get_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                # Verify the plain key matches the hashed key
                if verify_api_key(plain_key, data["key_hash"]):
                    return data
                return None
        except Exception as e:
            print(f"[Redis] Cache read error for {prefix}: {e}")

    # 2. Fall back to MongoDB (Beanie)
    from app.models.api_key import APIKey
    key_doc = await APIKey.find_one(APIKey.key_prefix == prefix)
    if not key_doc:
        return None

    # Verify the plain key matches MongoDB's stored hash
    if not verify_api_key(plain_key, key_doc.key_hash):
        return None

    # Prepare cached metadata
    data = {
        "id": str(key_doc.id),
        "key_hash": key_doc.key_hash,
        "plan": str(key_doc.plan),
        "is_active": key_doc.is_active,
    }

    # Write to Redis cache with 5-minute (300 seconds) expiration
    if redis:
        try:
            await redis.setex(cache_key, 300, json.dumps(data))
        except Exception as e:
            print(f"[Redis] Cache write error for {prefix}: {e}")

    return data


async def evict_key_cache(prefix: str) -> None:
    """
    Evicts the API key metadata from Redis cache.
    """
    redis = get_redis()
    if redis:
        try:
            await redis.delete(f"rateguard:key_cache:{prefix}")
        except Exception as e:
            print(f"[Redis] Cache eviction error for {prefix}: {e}")


async def check_rate_limit(plain_key: str, plan_tier: str) -> tuple[bool, int, int]:
    """
    Performs sliding-window rate limit checks using a Redis Lua script.
    Returns:
        (allowed: bool, remaining_capacity: int, total_limit: int)
    """
    prefix = plain_key[:16]
    limit = getattr(settings, f"RATE_LIMIT_{plan_tier.upper()}", settings.RATE_LIMIT_FREE)
    window = settings.RATE_LIMIT_WINDOW

    redis = get_redis()
    if not redis:
        # Fallback to fail-open if Redis is unavailable
        print("[Redis] Redis client unavailable. Rate limiting bypassed (fail-open).")
        return True, limit, limit

    rate_key = f"rateguard:rate_limit:{prefix}"
    now = time.time()
    member = f"{now}_{uuid.uuid4()}"

    try:
        res = await redis.eval(LUA_SLIDING_WINDOW, 1, rate_key, now, window, limit, member)
        allowed = bool(res[0])
        remaining = int(res[1])
        return allowed, remaining, limit
    except Exception as e:
        print(f"[Redis] Rate limiter Lua script execution error: {e}")
        # Fallback to fail-open
        return True, limit, limit
