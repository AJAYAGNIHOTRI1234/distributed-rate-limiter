import pytest
from app.models.user import User
from app.services.auth_service import issue_token_pair

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "RateGuard"

@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401  # no bearer header → 401 from HTTPBearer

@pytest.mark.asyncio
async def test_google_login_redirects(client):
    resp = await client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers["location"]

@pytest.mark.asyncio
async def test_token_refresh(client):
    # Setup a dummy user
    user = User(email="test@example.com", name="Test User", google_id="google-123")
    await user.insert()
    
    # Issue tokens
    tokens = await issue_token_pair(user)
    
    # Try refresh
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens.refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != tokens.access_token

@pytest.mark.asyncio
async def test_logout(client):
    # Setup dummy user and tokens
    user = User(email="logout@example.com", name="Logout User", google_id="google-logout")
    await user.insert()
    tokens = await issue_token_pair(user)
    
    # Logout
    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens.refresh_token})
    assert resp.status_code == 204
    
    # Try refresh again -> should fail
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens.refresh_token})
    assert resp.status_code == 401
