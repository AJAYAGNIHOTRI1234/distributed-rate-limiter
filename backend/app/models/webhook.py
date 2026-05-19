import secrets
from datetime import UTC, datetime
from beanie import Document, Indexed
from pydantic import Field


class WebhookSetting(Document):
    user_id: Indexed(str, unique=True)
    url: str | None = None
    secret: str = Field(default_factory=lambda: "whsec_" + secrets.token_urlsafe(24))
    is_active: bool = True
    events: list[str] = Field(default_factory=lambda: ["quota.approaching", "quota.exceeded", "rate_limit.exceeded"])
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "webhook_settings"
        indexes = ["user_id"]
