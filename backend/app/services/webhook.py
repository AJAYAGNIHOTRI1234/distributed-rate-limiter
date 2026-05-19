import hashlib
import hmac
import json
import time
import secrets
from datetime import UTC, datetime
import httpx

from app.models.webhook import WebhookSetting


class WebhookService:
    @staticmethod
    async def trigger_webhook(user_id: str, event: str, payload_data: dict) -> None:
        """
        Loads the user's active WebhookSetting, generates a secure HMAC-SHA256 signature,
        and posts the JSON payload asynchronously to the user's target URL.
        """
        # Fetch the webhook settings for this user
        webhook_setting = await WebhookSetting.find_one(WebhookSetting.user_id == user_id)
        if not webhook_setting:
            return

        if not webhook_setting.is_active or not webhook_setting.url:
            return

        if event not in webhook_setting.events:
            return

        # Prepare payload
        payload = {
            "id": "evt_" + secrets.token_urlsafe(16),
            "event": event,
            "created_at": datetime.now(UTC).isoformat(),
            "data": payload_data,
        }
        payload_str = json.dumps(payload)

        # Generate HMAC-SHA256 signature (Stripe standard)
        timestamp = str(int(time.time()))
        message = f"{timestamp}.{payload_str}".encode("utf-8")
        signature = hmac.new(
            webhook_setting.secret.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-RateGuard-Signature": f"t={timestamp},v1={signature}",
            "User-Agent": "RateGuard-Webhook-Dispatcher/1.0",
        }

        # Dispatch async HTTP request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_setting.url,
                    content=payload_str,
                    headers=headers,
                    timeout=5.0,
                )
                print(
                    f"[Webhook] Sent '{event}' to {webhook_setting.url}. "
                    f"Response: {response.status_code}"
                )
        except Exception as e:
            print(f"[Webhook] Delivery failed for '{event}' to {webhook_setting.url}: {e}")

    @staticmethod
    async def send_test_webhook(url: str, secret: str) -> tuple[int, str]:
        """
        Dispatches a dummy test event immediately to verify connection.
        Returns: (status_code, response_body)
        """
        payload = {
            "id": "evt_test_" + secrets.token_urlsafe(8),
            "event": "test.ping",
            "created_at": datetime.now(UTC).isoformat(),
            "data": {
                "message": "Hello from RateGuard! This is a test webhook.",
                "verified": True,
            },
        }
        payload_str = json.dumps(payload)

        timestamp = str(int(time.time()))
        message = f"{timestamp}.{payload_str}".encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-RateGuard-Signature": f"t={timestamp},v1={signature}",
            "User-Agent": "RateGuard-Webhook-Dispatcher/1.0",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=payload_str,
                    headers=headers,
                    timeout=5.0,
                )
                # Cap the body length to avoid huge logs
                body = response.text[:200]
                return response.status_code, body
        except httpx.RequestError as e:
            return 500, f"Request error: {e}"
        except Exception as e:
            return 500, f"Error: {e}"
