
from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    scopes: list[str] = Field(default_factory=lambda: ["read"])


class APIKeyOut(BaseModel):
    id: str
    name: str
    key_preview: str
    plan: str
    scopes: list[str]
    is_active: bool
    created_at: str
    last_used: str | None
    request_count: int
    requests_today: int


class APIKeyCreated(APIKeyOut):
    """Returned ONCE on creation — includes the raw key."""
    raw_key: str



