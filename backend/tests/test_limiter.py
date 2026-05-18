import pytest
from app.core.config import settings
from app.models.user import User
from app.services.auth_service import issue_token_pair
from app.db.redis_client import get_redis


@pytest.mark.asyncio
async def test_rate_limiter_full_flow(client):
    # 1. Setup user and get auth headers
    user = User(email="limiter@example.com", name="Limiter User", google_id="google-limiter")
    await user.insert()
    tokens = await issue_token_pair(user)
    auth_headers = {"Authorization": f"Bearer {tokens.access_token}"}

    # 2. Create an API Key in the database
    key_resp = await client.post("/api/v1/keys", json={"name": "Limiter Key"}, headers=auth_headers)
    assert key_resp.status_code == 201
    key_data = key_resp.json()
    raw_key = key_data["raw_key"]
    key_id = key_data["id"]

    # 3. Test Limiter Check using X-API-Key Header
    headers = {"X-API-Key": raw_key}
    resp = await client.post("/api/v1/limiter/check", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["limit"] == settings.RATE_LIMIT_FREE
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert "X-RateLimit-Reset" in resp.headers

    # 4. Test Limiter Check using Authorization Bearer Header
    bearer_headers = {"Authorization": f"Bearer {raw_key}"}
    resp = await client.post("/api/v1/limiter/check", headers=bearer_headers)
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True

    # 5. Test Limiter Check using Query Parameter
    resp = await client.post(f"/api/v1/limiter/check?api_key={raw_key}")
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True

    # 6. Test Limiter Check with missing key
    resp = await client.post("/api/v1/limiter/check")
    assert resp.status_code == 401
    assert "API Key missing" in resp.json()["detail"]

    # 7. Test Limiter Check with invalid key
    resp = await client.post("/api/v1/limiter/check", headers={"X-API-Key": "rg_live_invalidkeyvaluehere"})
    assert resp.status_code == 401
    assert "Invalid or inactive API key" in resp.json()["detail"]

    # 8. Test sliding window rate limit enforcement
    # Override settings for testing: limit = 3
    original_limit = settings.RATE_LIMIT_FREE
    settings.RATE_LIMIT_FREE = 3

    # Clear rate limits/cache in Redis for a clean test environment
    redis = get_redis()
    prefix = raw_key[:16]
    if redis:
        await redis.delete(f"rateguard:rate_limit:{prefix}")

    try:
        # Request 1 (remaining should be 2)
        resp = await client.post("/api/v1/limiter/check", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["remaining"] == 2

        # Request 2 (remaining should be 1)
        resp = await client.post("/api/v1/limiter/check", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["remaining"] == 1

        # Request 3 (remaining should be 0)
        resp = await client.post("/api/v1/limiter/check", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["remaining"] == 0

        # Request 4 (should be rate limited!)
        resp = await client.post("/api/v1/limiter/check", headers=headers)
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded."
        assert resp.headers["X-RateLimit-Remaining"] == "0"
    finally:
        # Restore settings
        settings.RATE_LIMIT_FREE = original_limit

    # 9. Test Revocation cache eviction
    # Revoke key
    rev_resp = await client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
    assert rev_resp.status_code == 204

    # The next check call should return 401 immediately (evicted from cache)
    resp = await client.post("/api/v1/limiter/check", headers=headers)
    assert resp.status_code == 401
    assert "Invalid or inactive API key" in resp.json()["detail"]
