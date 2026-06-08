from fastapi import HTTPException, status

from app.core.security import hash_api_key
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyOut


def _to_api_key_out(api_key: APIKey) -> APIKeyOut:
    return APIKeyOut(
        id=str(api_key.id),
        name=api_key.name,
        key_preview=api_key.key_prefix,
        plan=str(api_key.plan),
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
        last_used=api_key.last_used.isoformat() if api_key.last_used else None,
        request_count=api_key.requests_total,
        requests_today=api_key.requests_today,
    )


async def list_api_keys(user: User) -> list[APIKeyOut]:
    keys = await APIKey.find(APIKey.user_id == str(user.id)).to_list()
    return [_to_api_key_out(key) for key in keys]


PLAN_KEY_LIMITS: dict[str, int] = {"free": 3, "pro": 20, "enterprise": 100}


async def create_api_key(user: User, body: APIKeyCreate) -> APIKeyCreated:
    plan = str(getattr(user, "plan", "free"))
    limit = PLAN_KEY_LIMITS.get(plan, 3)

    active_count = await APIKey.find(
        APIKey.user_id == str(user.id),
        APIKey.is_active == True,  # noqa: E712
    ).count()

    if active_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Key limit reached for the '{plan}' plan. Maximum {limit} active key(s) allowed. Revoke an existing key or upgrade your plan.",
        )

    raw_key, prefix = APIKey.generate_raw_key()
    key_hash = hash_api_key(raw_key)

    api_key = APIKey(
        user_id=str(user.id),
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        plan=getattr(user, "plan", "free"),
        scopes=body.scopes,
    )
    await api_key.insert()

    return APIKeyCreated(**_to_api_key_out(api_key).model_dump(), raw_key=raw_key)


async def revoke_api_key(user: User, key_id: str) -> None:
    api_key = await APIKey.get(key_id)
    if not api_key or api_key.user_id != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    api_key.is_active = False
    await api_key.save()

    # Evict API Key metadata from Redis cache to disable it immediately
    from app.services.rate_limiter import evict_key_cache
    await evict_key_cache(api_key.key_prefix)


async def rotate_api_key(user: User, key_id: str) -> APIKeyCreated:
    api_key = await APIKey.get(key_id)
    if not api_key or api_key.user_id != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    api_key.is_active = False
    await api_key.save()

    # Evict rotated API Key metadata from Redis cache
    from app.services.rate_limiter import evict_key_cache
    await evict_key_cache(api_key.key_prefix)

    raw_key, prefix = APIKey.generate_raw_key()
    key_hash = hash_api_key(raw_key)

    rotated = APIKey(
        user_id=str(user.id),
        name=api_key.name,
        key_prefix=prefix,
        key_hash=key_hash,
        plan=api_key.plan,
        scopes=api_key.scopes,
    )
    await rotated.insert()
    return APIKeyCreated(**_to_api_key_out(rotated).model_dump(), raw_key=raw_key)
