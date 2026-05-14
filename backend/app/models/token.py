from datetime import UTC, datetime, timedelta

from beanie import Document, Indexed
from pydantic import Field

from app.core.config import settings


class RefreshToken(Document):
    user_id: str
    token_hash: Indexed(str, unique=True)
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
        + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    user_agent: str | None = None
    ip_address: str | None = None

    class Settings:
        name = "refresh_tokens"
        indexes = [
            [("token_hash", 1)],
            [("user_id", 1)],
        ]

    def is_valid(self) -> bool:
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return not self.is_revoked and datetime.now(UTC) < expires_at
