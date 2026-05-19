import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import User
from app.models.api_key import APIKey
from app.models.webhook import WebhookSetting
from app.services.auth_service import issue_token_pair


@pytest.mark.asyncio
async def test_webhook_settings_lifecycle(client: AsyncClient):
    # 1. Setup user and auth
    user = User(email="webhook@example.com", name="Webhook User", google_id="google-wh")
    await user.insert()
    tokens = await issue_token_pair(user)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}

    # 2. GET Webhook settings (should create default settings since they don't exist yet)
    resp = await client.get("/api/v1/webhooks", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert data["url"] is None
    assert "secret" in data
    assert data["secret"].startswith("whsec_")
    assert data["is_active"] is True
    assert "events" in data
    assert "quota.exceeded" in data["events"]

    # 3. PUT Webhook settings (update URL and events list)
    update_payload = {
        "url": "https://test.my-app.com/webhooks",
        "is_active": True,
        "events": ["quota.exceeded", "rate_limit.exceeded"]
    }
    resp = await client.put("/api/v1/webhooks", json=update_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://test.my-app.com/webhooks"
    assert data["events"] == ["quota.exceeded", "rate_limit.exceeded"]

    # 4. GET again and verify persistency in MongoDB
    resp = await client.get("/api/v1/webhooks", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://test.my-app.com/webhooks"
    assert data["events"] == ["quota.exceeded", "rate_limit.exceeded"]


@pytest.mark.asyncio
async def test_webhook_test_trigger_bad_url(client: AsyncClient):
    # 1. Setup user and auth
    user = User(email="webhook2@example.com", name="Webhook User 2", google_id="google-wh2")
    await user.insert()
    tokens = await issue_token_pair(user)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}

    # Test dispatching a test ping to an invalid URL protocol
    resp = await client.post(
        "/api/v1/webhooks/test",
        json={"url": "ftp://my-app.com", "secret": "whsec_test123"},
        headers=headers
    )
    assert resp.status_code == 400
    assert "Invalid URL protocol" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_quota_limits_headers_and_blocks(client: AsyncClient):
    # 1. Setup user and auth
    user = User(email="quota@example.com", name="Quota User", google_id="google-quota")
    await user.insert()
    tokens = await issue_token_pair(user)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}

    # 2. Create a fresh API Key for the user (returns 201 Created)
    resp = await client.post(
        "/api/v1/keys",
        json={"name": "Quota Test Key", "scopes": ["read"]},
        headers=headers
    )
    assert resp.status_code == 201
    key_data = resp.json()
    plain_key = key_data["raw_key"]

    # 3. Perform /check endpoint call (should succeed and attach quota headers)
    resp = await client.post(
        "/api/v1/limiter/check",
        headers={"X-API-Key": plain_key}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert "quota_remaining" in data
    assert "quota_limit" in data
    assert data["quota_limit"] == settings.QUOTA_LIMIT_FREE

    # Check response headers
    resp_headers = resp.headers
    assert "X-Quota-Limit" in resp_headers
    assert "X-Quota-Remaining" in resp_headers
    assert "X-Quota-Reset" in resp_headers
    assert int(resp_headers["X-Quota-Limit"]) == settings.QUOTA_LIMIT_FREE
    assert int(resp_headers["X-Quota-Remaining"]) == settings.QUOTA_LIMIT_FREE - 1

    # 4. Artificially simulate daily quota exhaustion
    # Locate the key preview prefix (first 16 chars)
    prefix = plain_key[:16]
    
    # We will increment the Redis quota counter to the daily limit
    from app.db.redis_client import get_redis
    from datetime import UTC, datetime
    redis = get_redis()
    assert redis is not None
    
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    quota_key = f"rateguard:quota:{prefix}:{today}"
    
    # Set daily quota usage directly to the limit in Redis
    await redis.set(quota_key, str(settings.QUOTA_LIMIT_FREE))

    # 5. Try making another request (should be blocked with 403 Forbidden due to quota limit exceeded)
    resp = await client.post(
        "/api/v1/limiter/check",
        headers={"X-API-Key": plain_key}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Daily quota exceeded."
    
    # Check that headers are still sent on blocked requests
    resp_headers = resp.headers
    assert int(resp_headers["X-Quota-Remaining"]) == 0
