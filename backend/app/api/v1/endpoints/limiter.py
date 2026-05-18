from datetime import UTC, datetime
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Response, status
from app.core.config import settings
from app.models.api_key import APIKey
from app.services.rate_limiter import check_rate_limit, get_key_metadata

router = APIRouter(prefix="/limiter", tags=["limiter"])


async def update_api_key_stats(key_id: str):
    """
    Background task to update request usage metrics for an API key in MongoDB.
    """
    try:
        key_doc = await APIKey.get(key_id)
        if key_doc:
            key_doc.requests_total += 1
            key_doc.requests_today += 1
            key_doc.last_used = datetime.now(UTC)
            await key_doc.save()
    except Exception as e:
        print(f"[Mongo] Error updating API Key stats for {key_id}: {e}")


@router.post("/check")
async def check_rate_limiting(
    response: Response,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
    api_key_query: str | None = Query(None, alias="api_key"),
):
    """
    Enforce rate limits on incoming API requests based on plan tiers.
    Accepts keys via:
    - X-API-Key header
    - Authorization: Bearer <key> header
    - api_key query parameter
    """
    # 1. Resolve plain API key from supported sources
    plain_key = None
    if x_api_key:
        plain_key = x_api_key
    elif authorization and authorization.lower().startswith("bearer "):
        plain_key = authorization[7:]
    elif api_key_query:
        plain_key = api_key_query

    if not plain_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing. Provide it via X-API-Key header, Authorization Bearer token, or api_key query parameter.",
        )

    # 2. Retrieve key metadata (via Redis cache first)
    metadata = await get_key_metadata(plain_key)
    if not metadata or not metadata.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
        )

    # 3. Perform atomic rate limiting check
    allowed, remaining, limit = await check_rate_limit(plain_key, metadata["plan"])

    # 4. Set standard response headers
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(settings.RATE_LIMIT_WINDOW)

    # 5. Handle rate limit exceeded
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(settings.RATE_LIMIT_WINDOW),
            },
        )

    # 6. Schedule async statistics write-back
    background_tasks.add_task(update_api_key_stats, metadata["id"])

    return {
        "allowed": True,
        "remaining": remaining,
        "limit": limit,
    }
