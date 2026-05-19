from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.deps import get_current_user
from app.models.user import User
from app.models.webhook import WebhookSetting
from app.services.webhook import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookUpdate(BaseModel):
    url: str | None = Field(None, max_length=500)
    is_active: bool = True
    events: list[str] = Field(default_factory=lambda: ["quota.approaching", "quota.exceeded", "rate_limit.exceeded"])


class WebhookTestRequest(BaseModel):
    url: str
    secret: str


@router.get("")
async def get_webhook_config(user: User = Depends(get_current_user)):
    setting = await WebhookSetting.find_one(WebhookSetting.user_id == str(user.id))
    if not setting:
        # Create one with default values if it doesn't exist yet
        setting = WebhookSetting(user_id=str(user.id))
        await setting.insert()

    return {
        "url": setting.url,
        "secret": setting.secret,
        "is_active": setting.is_active,
        "events": setting.events,
    }


@router.put("")
async def update_webhook_config(body: WebhookUpdate, user: User = Depends(get_current_user)):
    # Simple URL check if provided
    if body.url:
        u = body.url.strip()
        if not (u.startswith("http://") or u.startswith("https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL protocol. Webhook URL must start with http:// or https://",
            )
        url_val = u
    else:
        url_val = None

    setting = await WebhookSetting.find_one(WebhookSetting.user_id == str(user.id))
    if not setting:
        setting = WebhookSetting(
            user_id=str(user.id),
            url=url_val,
            is_active=body.is_active,
            events=body.events,
        )
        await setting.insert()
    else:
        setting.url = url_val
        setting.is_active = body.is_active
        setting.events = body.events
        await setting.save()

    return {
        "url": setting.url,
        "secret": setting.secret,
        "is_active": setting.is_active,
        "events": setting.events,
    }


@router.post("/test")
async def test_webhook(body: WebhookTestRequest, user: User = Depends(get_current_user)):
    url = body.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL protocol. Webhook URL must start with http:// or https://",
        )

    status_code, response_body = await WebhookService.send_test_webhook(url, body.secret)
    return {
        "status_code": status_code,
        "response": response_body,
    }
