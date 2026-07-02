import httpx
import pytest
import respx

from alita_agent.tools import login
from tests.conftest import FakeToolContext

TEST_BASE_URL = "http://test-ecommerce-api"


@respx.mock
async def test_login_success_writes_token_to_state(test_client, tool_context):
    """AC-AUTH-U06"""
    respx.post(f"{TEST_BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "jwt-abc",
                "refresh_token": "refresh-abc",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )
    )

    result = await login("user@example.com", "correct-password", tool_context)

    assert result == {"status": "success", "message": "Login realizado com sucesso."}
    assert tool_context.state["access_token"] == "jwt-abc"


@respx.mock
async def test_login_invalid_credentials_returns_friendly_error(test_client):
    """AC-AUTH-U07"""
    respx.post(f"{TEST_BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(401, json={"detail": "Invalid email or password."})
    )
    empty_context = FakeToolContext()

    result = await login("user@example.com", "wrong-password", empty_context)

    assert result == {"status": "error", "message": "Email ou senha inválidos."}
    assert "access_token" not in empty_context.state


@respx.mock
async def test_login_bad_request_returns_friendly_error(test_client, tool_context):
    """AC-AUTH-U08"""
    respx.post(f"{TEST_BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(400, json={"detail": "Malformed request."})
    )

    result = await login("not-an-email", "x", tool_context)

    assert result == {"status": "error", "message": "Email ou senha inválidos."}


@respx.mock
async def test_login_server_error_propagates(test_client, tool_context):
    """AC-AUTH-U09"""
    respx.post(f"{TEST_BASE_URL}/api/v1/auth/login").mock(
        return_value=httpx.Response(500, json={"detail": "Internal error."})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await login("user@example.com", "whatever", tool_context)
