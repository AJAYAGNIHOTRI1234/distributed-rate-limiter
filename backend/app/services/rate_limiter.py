import asyncio
import time
import uuid
import json
from datetime import UTC, datetime
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
                # Check key expiry from cached metadata
                exp_str = data.get("expires_at")
                if exp_str:
                    exp = datetime.fromisoformat(exp_str)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=UTC)
                    if datetime.now(UTC) >= exp:
                        return None
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

    # Reject expired keys
    if key_doc.expires_at is not None:
        exp = key_doc.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if datetime.now(UTC) >= exp:
            return None

    # Prepare cached metadata
    data = {
        "id": str(key_doc.id),
        "user_id": str(key_doc.user_id),
        "key_hash": key_doc.key_hash,
        "plan": str(key_doc.plan),
        "is_active": key_doc.is_active,
        "expires_at": key_doc.expires_at.isoformat() if key_doc.expires_at else None,
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


async def trigger_webhook_with_dedup(
    user_id: str, event: str, prefix: str, today: str, payload_data: dict
) -> None:
    redis = get_redis()
    if not redis:
        return
    flag_key = f"rateguard:webhook_flag:{prefix}:{event}:{today}"
    already_set = await redis.get(flag_key)
    if not already_set:
        await redis.setex(flag_key, 36 * 3600, "1")
        from app.services.webhook import WebhookService
        asyncio.create_task(WebhookService.trigger_webhook(user_id, event, payload_data))


async def trigger_webhook_with_cooldown(
    user_id: str, event: str, prefix: str, cooldown_seconds: int, payload_data: dict
) -> None:
    redis = get_redis()
    if not redis:
        return
    flag_key = f"rateguard:webhook_flag:{prefix}:{event}:cooldown"
    already_set = await redis.get(flag_key)
    if not already_set:
        await redis.setex(flag_key, cooldown_seconds, "1")
        from app.services.webhook import WebhookService
        asyncio.create_task(WebhookService.trigger_webhook(user_id, event, payload_data))


async def check_quota_and_limit(
    plain_key: str, plan_tier: str, user_id: str
) -> tuple[bool, str, int, int, int, int]:
    """
    Checks the daily quota usage and sliding-window rate limit using Redis.
    Returns:
        (allowed: bool, reject_reason: str, remaining_window: int, window_limit: int, current_daily: int, daily_limit: int)
    """
    prefix = plain_key[:16]
    daily_limit = getattr(settings, f"QUOTA_LIMIT_{plan_tier.upper()}", settings.QUOTA_LIMIT_FREE)
    window_limit = getattr(settings, f"RATE_LIMIT_{plan_tier.upper()}", settings.RATE_LIMIT_FREE)
    window = settings.RATE_LIMIT_WINDOW

    redis = get_redis()
    if not redis:
        # Fallback to fail-open if Redis is down
        return True, "", window_limit, window_limit, 0, daily_limit

    # 1. Check Daily Quota
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    quota_key = f"rateguard:quota:{prefix}:{today}"

    current_val = await redis.get(quota_key)
    current_daily = int(current_val) if current_val else 0

    if current_daily >= daily_limit:
        # Trigger quota.exceeded webhook (deduplicated)
        await trigger_webhook_with_dedup(
            user_id,
            "quota.exceeded",
            prefix,
            today,
            {
                "key_prefix": prefix,
                "plan": plan_tier,
                "requests_today": current_daily,
                "quota_limit": daily_limit,
                "percentage": 100.0,
            }
        )
        return False, "quota_exceeded", 0, window_limit, current_daily, daily_limit

    # 2. Check Sliding Window Rate Limit
    rate_key = f"rateguard:rate_limit:{prefix}"
    now = time.time()
    member = f"{now}_{uuid.uuid4()}"

    try:
        res = await redis.eval(LUA_SLIDING_WINDOW, 1, rate_key, now, window, window_limit, member)
        allowed = bool(res[0])
        remaining = int(res[1])
    except Exception as e:
        print(f"[Redis] Rate limiter Lua script execution error: {e}")
        # Fallback to fail-open
        return True, "", window_limit, window_limit, current_daily, daily_limit

    if not allowed:
        # Trigger rate_limit.exceeded webhook with a 5-minute cooldown to prevent spamming
        await trigger_webhook_with_cooldown(
            user_id,
            "rate_limit.exceeded",
            prefix,
            300,
            {
                "key_prefix": prefix,
                "plan": plan_tier,
                "window_size_seconds": window,
                "rate_limit": window_limit,
            }
        )
        return False, "rate_limit_exceeded", remaining, window_limit, current_daily, daily_limit

    # 3. Successful request: Increment Daily Quota atomically
    new_daily = await redis.incr(quota_key)
    if new_daily == 1:
        await redis.expire(quota_key, 36 * 3600)  # 36 hours TTL

    # 4. Check warning and limit thresholds for Webhooks
    pct = new_daily / daily_limit
    if pct >= 1.0:
        await trigger_webhook_with_dedup(
            user_id,
            "quota.exceeded",
            prefix,
            today,
            {
                "key_prefix": prefix,
                "plan": plan_tier,
                "requests_today": new_daily,
                "quota_limit": daily_limit,
                "percentage": 100.0,
            }
        )
    elif pct >= 0.8:
        await trigger_webhook_with_dedup(
            user_id,
            "quota.approaching",
            prefix,
            today,
            {
                "key_prefix": prefix,
                "plan": plan_tier,
                "requests_today": new_daily,
                "quota_limit": daily_limit,
                "percentage": round(pct * 100, 1),
            }
        )

    return True, "", remaining, window_limit, new_daily, daily_limit
