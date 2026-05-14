import pytest
from app.models.user import User
from app.services.auth_service import issue_token_pair

@pytest.mark.asyncio
async def test_key_lifecycle(client):
    # 1. Setup user and auth
    user = User(email="keys@example.com", name="Key User", google_id="google-keys")
    await user.insert()
    tokens = await issue_token_pair(user)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    
    # 2. Create Key
    resp = await client.post("/api/v1/keys", json={"name": "Test Key"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "raw_key" in data
    assert data["name"] == "Test Key"
    key_id = data["id"]
    
    # 3. List Keys
    resp = await client.get("/api/v1/keys", headers=headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) >= 1
    assert any(k["id"] == key_id for k in keys)
    
    # 4. Rotate Key
    resp = await client.post(f"/api/v1/keys/{key_id}/rotate", headers=headers)
    assert resp.status_code == 200
    new_data = resp.json()
    assert "raw_key" in new_data
    assert new_data["id"] != key_id
    new_key_id = new_data["id"]
    
    # 5. Verify old key is revoked (list keys should show it as inactive or it might be filtered)
    # The current list_api_keys returns all keys for user. Let's check is_active.
    resp = await client.get("/api/v1/keys", headers=headers)
    keys = resp.json()
    old_key = next(k for k in keys if k["id"] == key_id)
    assert old_key["is_active"] is False
    
    # 6. Revoke new key
    resp = await client.delete(f"/api/v1/keys/{new_key_id}", headers=headers)
    assert resp.status_code == 204
    
    # Verify it's revoked
    resp = await client.get("/api/v1/keys", headers=headers)
    keys = resp.json()
    revoked_key = next(k for k in keys if k["id"] == new_key_id)
    assert revoked_key["is_active"] is False
