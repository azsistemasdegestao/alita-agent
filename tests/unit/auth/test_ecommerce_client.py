import time

import httpx
import pytest
import respx

from alita_agent.ecommerce_client import EcommerceClient

BASE_URL = "http://test-ecommerce-api"


@pytest.fixture
def client() -> EcommerceClient:
    return EcommerceClient(base_url=BASE_URL)


@respx.mock
async def test_request_with_token_bypasses_dev_login(client: EcommerceClient):
    """AC-AUTH-U01"""
    route = respx.get(f"{BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    login_route = respx.post(f"{BASE_URL}/api/v1/auth/login")

    resp = await client.request("GET", "/api/v1/orders", token="user-token")

    assert resp.status_code == 200
    assert route.calls.last.request.headers["Authorization"] == "Bearer user-token"
    assert login_route.call_count == 0


@respx.mock
async def test_request_with_no_token_triggers_dev_login(
    client: EcommerceClient, monkeypatch
):
    """AC-AUTH-U02"""
    monkeypatch.setenv("ECOMMERCE_AGENT_EMAIL", "dev@example.com")
    monkeypatch.setenv("ECOMMERCE_AGENT_PASSWORD", "dev-pass")

    login_route = respx.post(f"{BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "dev-token",
                "refresh_token": "dev-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )
    orders_route = respx.get(f"{BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    resp = await client.request("GET", "/api/v1/orders")

    assert resp.status_code == 200
    assert login_route.call_count == 1
    body = login_route.calls.last.request.content
    assert b"dev@example.com" in body
    assert orders_route.calls.last.request.headers["Authorization"] == "Bearer dev-token"


@respx.mock
async def test_request_with_no_token_reuses_cached_token(
    client: EcommerceClient, monkeypatch
):
    """AC-AUTH-U03"""
    monkeypatch.setenv("ECOMMERCE_AGENT_EMAIL", "dev@example.com")
    monkeypatch.setenv("ECOMMERCE_AGENT_PASSWORD", "dev-pass")

    login_route = respx.post(f"{BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "dev-token",
                "refresh_token": "dev-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )
    respx.get(f"{BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    await client.request("GET", "/api/v1/orders")
    await client.request("GET", "/api/v1/orders")

    assert login_route.call_count == 1


@respx.mock
async def test_request_with_no_token_refreshes_expired_token(
    client: EcommerceClient, monkeypatch
):
    """AC-AUTH-U04"""
    monkeypatch.setenv("ECOMMERCE_AGENT_EMAIL", "dev@example.com")
    monkeypatch.setenv("ECOMMERCE_AGENT_PASSWORD", "dev-pass")

    # Prime the client with an already-expired cached token + refresh token.
    client._access_token = "old-token"
    client._refresh_token = "old-refresh"
    client._expires_at = time.time() - 1

    login_route = respx.post(f"{BASE_URL}/api/v1/auth/login")
    refresh_route = respx.post(f"{BASE_URL}/api/v1/auth/refresh").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "refreshed-token",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )
    orders_route = respx.get(f"{BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    await client.request("GET", "/api/v1/orders")

    assert refresh_route.call_count == 1
    assert login_route.call_count == 0
    assert orders_route.calls.last.request.headers["Authorization"] == "Bearer refreshed-token"


@respx.mock
async def test_login_returns_raw_tokens_without_storing_state(client: EcommerceClient):
    """AC-AUTH-U05"""
    respx.post(f"{BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "some-token",
                "refresh_token": "some-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )

    data = await client.login("someone@example.com", "s3cr3t")

    assert data["access_token"] == "some-token"
    assert client._access_token is None
