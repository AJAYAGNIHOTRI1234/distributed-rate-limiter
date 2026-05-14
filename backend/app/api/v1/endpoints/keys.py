from fastapi import APIRouter, Depends, status

from app.middleware.deps import get_current_user
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyOut
from app.services.api_key_service import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
    rotate_api_key,
)

router = APIRouter(prefix="/keys", tags=["api-keys"])


@router.get("", response_model=list[APIKeyOut])
async def list_keys(user: User = Depends(get_current_user)):
    return await list_api_keys(user)


@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(body: APIKeyCreate, user: User = Depends(get_current_user)):
    """Create a new API key. The raw key is returned ONCE — store it securely."""
    return await create_api_key(user, body)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(key_id: str, user: User = Depends(get_current_user)):
    await revoke_api_key(user, key_id)


@router.post("/{key_id}/rotate", response_model=APIKeyCreated)
async def rotate_key(key_id: str, user: User = Depends(get_current_user)):
    """Revoke a key and issue a new one with the same settings."""
    return await rotate_api_key(user, key_id)
