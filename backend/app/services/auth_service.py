from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_api_key,
    verify_password,
    verify_token,
)
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenPair


async def upsert_google_user(user_info: dict[str, Any]) -> tuple[User, bool]:
    """Find or create a user from Google user info. Returns (user, is_new)."""
    google_id = user_info["sub"]
    email = user_info["email"]
    name = user_info.get("name", "")
    avatar = user_info.get("picture")

    user = await User.find_one(User.google_id == google_id)
    if user:
        user.last_login = datetime.now(UTC)
        user.avatar = avatar
        await user.save()
        return user, False

    # Check if email already exists (different Google account)
    existing = await User.find_one(User.email == email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already registered with a password. Please sign in with your email and password instead.",
        )

    user = User(
        email=email,
        name=name,
        avatar=avatar,
        google_id=google_id,
        last_login=datetime.now(UTC),
    )
    await user.insert()
    return user, True


async def register_user(data: dict[str, Any]) -> tuple[User, bool]:
    """Register a new user with email and password."""
    email = data["email"]
    password = data["password"]
    name = f"{data['first_name']} {data['last_name']}".strip()
    plan = data.get("plan", "free")

    # Check if email already exists
    existing = await User.find_one(User.email == email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=email,
        name=name,
        hashed_password=get_password_hash(password),
        plan=plan,
        last_login=datetime.now(UTC),
    )
    await user.insert()
    return user, True


async def authenticate_user(email: str, password: str) -> User:
    """Authenticate a user with email and password."""
    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses Google Sign-In. Please sign in with Google.",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated.",
        )

    user.last_login = datetime.now(UTC)
    await user.save()
    return user


async def issue_token_pair(
    user: User,
    user_agent: str = "",
    ip: str = "",
) -> TokenPair:
    """Create access + refresh token pair and persist the refresh token."""
    user_id = str(user.id)
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    token_hash = hash_api_key(refresh_token)
    refresh_doc = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip,
    )
    await refresh_doc.insert()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(refresh_token: str) -> TokenPair:
    """Validate refresh token, revoke it, and issue a new token pair."""
    user_id = verify_token(refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # Find matching token document
    token_doc = await _find_refresh_token(refresh_token)
    if not token_doc or not token_doc.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired.",
        )

    # Revoke old token (rotation)
    token_doc.is_revoked = True
    await token_doc.save()

    user = await User.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated.",
        )

    return await issue_token_pair(
        user,
        user_agent=token_doc.user_agent or "",
        ip=token_doc.ip_address or "",
    )


async def revoke_refresh_token(refresh_token: str) -> None:
    """Revoke a refresh token (logout)."""
    token_doc = await _find_refresh_token(refresh_token)
    if token_doc:
        token_doc.is_revoked = True
        await token_doc.save()


async def _find_refresh_token(raw_token: str) -> RefreshToken | None:
    """Find a RefreshToken document by verifying the hash against all user tokens."""
    from app.core.security import verify_api_key

    user_id = verify_token(raw_token, token_type="refresh")
    if not user_id:
        return None

    candidates = await RefreshToken.find(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,  # noqa: E712
    ).to_list()

    for doc in candidates:
        if verify_api_key(raw_token, doc.token_hash):
            return doc
    return None
