from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(Document):
    email: Indexed(EmailStr, unique=True)
    name: str
    avatar: str | None = None
    hashed_password: str | None = None
    google_id: Indexed(str, unique=True, sparse=True) | None = None
    role: UserRole = UserRole.USER
    plan: str = "free"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "picture": self.avatar,
            "plan": self.plan,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
        }

    class Settings:
        name = "users"
        indexes = ["email", "google_id"]

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "google_id": "1234567890",
                "role": "user",
            }
        }
    }
