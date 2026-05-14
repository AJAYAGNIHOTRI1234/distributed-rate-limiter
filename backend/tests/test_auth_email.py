import pytest
from app.models.user import User

@pytest.mark.asyncio
async def test_register_success(client):
    email = "newuser_unique@example.com"
    # Ensure user doesn't exist
    existing = await User.find_one(User.email == email)
    if existing:
        await existing.delete()

    payload = {
        "email": email,
        "password": "strongpassword123",
        "first_name": "New",
        "last_name": "User",
        "plan": "free"
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "tokens" in data
    assert "user" in data
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["name"] == "New User"
    assert data["is_new_user"] is True

    # Verify user in DB
    user = await User.find_one(User.email == payload["email"])
    assert user is not None
    assert user.hashed_password is not None

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    # Setup existing user
    user = User(email="existing@example.com", name="Existing User", hashed_password="...")
    await user.insert()

    payload = {
        "email": "existing@example.com",
        "password": "password123",
        "first_name": "Other",
        "last_name": "User"
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_login_success(client):
    # Setup user
    email = "login@example.com"
    password = "correct-password"
    payload = {
        "email": email,
        "password": password,
        "first_name": "Login",
        "last_name": "User"
    }
    await client.post("/api/v1/auth/register", json=payload)

    # Login
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "tokens" in data
    assert data["user"]["email"] == email

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    # Setup user
    email = "wrongpass@example.com"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "real-password",
        "first_name": "Wrong",
        "last_name": "Pass"
    })

    # Login with wrong password
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123"
    })
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()
