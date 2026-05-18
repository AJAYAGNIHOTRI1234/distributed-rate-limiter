import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.db.redis_client import get_redis
from app.middleware.deps import get_current_user
from app.models.user import User
from app.schemas.auth import GoogleCallbackResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserOut
from app.services.auth_service import (
    authenticate_user,
    issue_token_pair,
    refresh_access_token,
    register_user,
    revoke_refresh_token,
    upsert_google_user,
)
from app.services.google_oauth import (
    exchange_code_for_tokens,
    get_google_auth_url,
    get_google_user_info,
)

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_STATE_TTL = 600  # 10 minutes


@router.get("/google/login")
async def google_login():
    """Redirect the browser to Google's consent screen."""
    state = secrets.token_urlsafe(16)
    redis = get_redis()
    await redis.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, "1")
    url = get_google_auth_url(state)
    return RedirectResponse(url)


@router.get("/google/callback", response_model=GoogleCallbackResponse)
async def google_callback(request: Request, code: str, state: str):
    """Google redirects here with an auth code."""
    redis = get_redis()
    if not await redis.exists(f"oauth_state:{state}"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state.")
    await redis.delete(f"oauth_state:{state}")

    try:
        google_tokens = await exchange_code_for_tokens(code)
        user_info = await get_google_user_info(google_tokens["access_token"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google error: {exc}"
        ) from exc

    user, is_new = await upsert_google_user(user_info)

    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else ""
    token_pair = await issue_token_pair(user, user_agent=user_agent, ip=client_ip)

    # In a browser flow you'd redirect to frontend with tokens in query params or cookies.
    # This returns JSON for a SPA / API-first setup.
    return GoogleCallbackResponse(
        tokens=token_pair,
        user=UserOut(**user.to_safe_dict()),
        is_new_user=is_new,
    )


@router.post("/register", response_model=GoogleCallbackResponse)
async def register(request: Request, body: RegisterRequest):
    """Register a new user with email and password."""
    user, is_new = await register_user(body.model_dump())

    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else ""
    token_pair = await issue_token_pair(user, user_agent=user_agent, ip=client_ip)

    return GoogleCallbackResponse(
        tokens=token_pair,
        user=UserOut(**user.to_safe_dict()),
        is_new_user=is_new,
    )


@router.post("/login", response_model=GoogleCallbackResponse)
async def login(request: Request, body: LoginRequest):
    """Authenticate a user with email and password."""
    user = await authenticate_user(body.email, body.password)

    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else ""
    token_pair = await issue_token_pair(user, user_agent=user_agent, ip=client_ip)

    return GoogleCallbackResponse(
        tokens=token_pair,
        user=UserOut(**user.to_safe_dict()),
        is_new_user=False,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest):
    return await refresh_access_token(body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest):
    await revoke_refresh_token(body.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(**user.to_safe_dict())
