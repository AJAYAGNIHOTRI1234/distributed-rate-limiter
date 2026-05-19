import pytest
from httpx import AsyncClient
from app.models.user import User
from app.services.auth_service import issue_token_pair

@pytest.mark.asyncio
async def test_root_prometheus_metrics(client: AsyncClient):
    """
    Asserts that the root /metrics scraper endpoint responds in valid Prometheus text format.
    """
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Verify standard Prometheus compliance markers
    assert "# HELP" in text
    assert "# TYPE" in text
    assert "rateguard_requests_total" in text
    assert "rateguard_request_latency_seconds" in text

@pytest.mark.asyncio
async def test_analytics_summary_gathering(client: AsyncClient):
    """
    Verifies that calling /check records active traffic telemetry, categorizes response codes,
    computes latencies (p50/p90/p99), and attributes traffic to key prefixes correctly.
    """
    # 1. Setup user and auth
    user = User(email="analytics-test@example.com", name="Analytics User", google_id="google-analytics")
    await user.insert()
    tokens = await issue_token_pair(user)
    auth_headers = {"Authorization": f"Bearer {tokens.access_token}"}

    # 2. Get summary initially (should return empty baseline datasets)
    resp = await client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert "hourly_requests" in summary
    assert len(summary["hourly_requests"]) == 24
    assert summary["status_breakdown"] == {"200": 0, "429": 0, "403": 0}
    assert summary["latency_metrics"] == {"p50": 0.0, "p90": 0.0, "p99": 0.0}
    assert summary["top_keys"] == []

    # 3. Create a fresh API Key for the user
    resp = await client.post(
        "/api/v1/keys",
        json={"name": "Analytics Key", "scopes": ["read"]},
        headers=auth_headers
    )
    assert resp.status_code == 201
    key_data = resp.json()
    plain_key = key_data["raw_key"]

    # 4. Trigger /check API requests to register hits
    check_resp = await client.post(
        "/api/v1/limiter/check",
        headers={"X-API-Key": plain_key}
    )
    assert check_resp.status_code == 200

    # 5. Fetch updated summary and check increments
    resp = await client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    summary = resp.json()
    
    # Assert hourly requests contains at least 1 hit
    assert sum(summary["hourly_requests"]) == 1
    assert summary["status_breakdown"]["200"] == 1
    assert summary["latency_metrics"]["p50"] >= 0.0
    assert len(summary["top_keys"]) == 1
    assert summary["top_keys"][0]["prefix"] == plain_key[:16]
    assert summary["top_keys"][0]["requests"] == 1
