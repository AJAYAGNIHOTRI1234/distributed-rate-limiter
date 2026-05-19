import asyncio
import httpx
from datetime import UTC, datetime
from app.core.config import settings
from app.db.redis_client import get_redis
from app.models.user import User
from app.models.webhook import WebhookSetting
from app.models.api_key import APIKey
from app.models.token import RefreshToken
from app.services.auth_service import issue_token_pair
from app.db.redis_client import init_redis, close_redis
import motor.motor_asyncio
from beanie import init_beanie as beanie_init

async def main():
    print("=== STARTING PHASE 4 END-TO-END VERIFICATION ===")
    
    # 1. Initialize DB Connection
    await init_redis()
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB]
    await beanie_init(database=db, document_models=[User, APIKey, WebhookSetting, RefreshToken])
    print("[DB] MongoDB Initialized.")

    # 2. Setup Test User
    email = "verify-e2e@example.com"
    await User.find(User.email == email).delete()
    user = User(email=email, name="E2E Verifier", google_id="e2e-google")
    await user.insert()
    print(f"[User] Created test user: {email}")

    # 3. Setup Webhook Configuration
    # We will point it to a mock receiver running on port 9090
    webhook_url = "http://localhost:9090/webhook"
    await WebhookSetting.find(WebhookSetting.user_id == str(user.id)).delete()
    webhook = WebhookSetting(
        user_id=str(user.id),
        url=webhook_url,
        secret="whsec_e2e_verification_secret_key_12345",
        is_active=True,
        events=["quota.approaching", "quota.exceeded", "rate_limit.exceeded"]
    )
    await webhook.insert()
    print(f"[Webhooks] Configured webhook endpoint: {webhook_url}")

    # 4. Generate API Key
    tokens = await issue_token_pair(user)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    
    async with httpx.AsyncClient() as http_client:
        # Create Key via API
        resp = await http_client.post(
            "http://127.0.0.1:8000/api/v1/keys",
            json={"name": "E2E Key", "scopes": ["read"]},
            headers=headers
        )
        assert resp.status_code == 201, f"Failed key creation: {resp.text}"
        key_data = resp.json()
        plain_key = key_data["raw_key"]
        prefix = plain_key[:16]
        print(f"[API Key] Generated Key: {plain_key} (Prefix: {prefix})")

        # 5. Make live rate limit and quota check
        print("\n--- Triggering Quota Check #1 (Expect success and headers) ---")
        resp = await http_client.post(
            "http://127.0.0.1:8000/api/v1/limiter/check",
            headers={"X-API-Key": plain_key}
        )
        print(f"HTTP Status: {resp.status_code}")
        print("Response headers:")
        for h in ["X-Quota-Limit", "X-Quota-Remaining", "X-Quota-Reset"]:
            print(f"  {h}: {resp.headers.get(h)}")
        
        assert resp.status_code == 200
        assert int(resp.headers.get("X-Quota-Remaining")) == settings.QUOTA_LIMIT_FREE - 1

        # 6. Simulate 80% quota warning threshold (800 / 1000)
        print("\n--- Simulating 80% quota warning threshold (800 / 1000) ---")
        redis = get_redis()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        quota_key = f"rateguard:quota:{prefix}:{today}"
        
        # Set quota key value in Redis to 799 so the next request hits 800 (80%)
        await redis.set(quota_key, "799")
        
        resp = await http_client.post(
            "http://127.0.0.1:8000/api/v1/limiter/check",
            headers={"X-API-Key": plain_key}
        )
        print(f"HTTP Status: {resp.status_code}")
        print(f"X-Quota-Remaining: {resp.headers.get('X-Quota-Remaining')}")
        
        # Let's wait a moment for the async background webhook dispatch to run
        await asyncio.sleep(1)

        # 7. Simulate 100% quota exhausted threshold (1000 / 1000)
        print("\n--- Simulating 100% quota exhausted threshold (1000 / 1000) ---")
        await redis.set(quota_key, "999")
        
        resp = await http_client.post(
            "http://127.0.0.1:8000/api/v1/limiter/check",
            headers={"X-API-Key": plain_key}
        )
        print(f"HTTP Status: {resp.status_code}")
        print(f"X-Quota-Remaining: {resp.headers.get('X-Quota-Remaining')}")
        
        await asyncio.sleep(1)

        # 8. Simulate 101% quota (blocked request)
        print("\n--- Simulating Quota Blocked request (> 1000) ---")
        await redis.set(quota_key, "1000")
        
        resp = await http_client.post(
            "http://127.0.0.1:8000/api/v1/limiter/check",
            headers={"X-API-Key": plain_key}
        )
        print(f"HTTP Status (Expect 403): {resp.status_code}")
        print(f"Response Detail: {resp.json().get('detail')}")
        print(f"X-Quota-Remaining: {resp.headers.get('X-Quota-Remaining')}")
        
        assert resp.status_code == 403
        assert resp.json().get("detail") == "Daily quota exceeded."

        # 9. Clean up
        await User.find(User.email == email).delete()
        await WebhookSetting.find(WebhookSetting.user_id == str(user.id)).delete()
        await close_redis()
        print("\n=== PHASE 4 END-TO-END VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
