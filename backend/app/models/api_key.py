import secrets
from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, Indexed
from pydantic import Field


class PlanTier(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class APIKey(Document):
    user_id: Indexed(str)
    name: str
    key_prefix: str                      # e.g. "rg_live_8xKp"  — visible
    key_hash: str                        # bcrypt hash of full key — never returned
    plan: PlanTier = PlanTier.FREE
    scopes: list[str] = ["read"]
    is_active: bool = True
    requests_today: int = 0
    requests_today_date: str | None = None   # YYYY-MM-DD — used to auto-reset requests_today at midnight
    requests_total: int = 0
    last_used: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    class Settings:
        name = "api_keys"
        indexes = ["user_id", "key_prefix"]

    @staticmethod
    def generate_raw_key() -> tuple[str, str]:
        """Returns (raw_key, prefix). Store raw_key once, then hash it."""
        raw = "rg_live_" + secrets.token_urlsafe(24)
        prefix = raw[:16]
        return raw, prefix
