import os
import uuid

import httpx
import pytest

from alita_agent import api
from alita_agent.ecommerce_client import client as ecommerce_client

pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"), reason="requires a real Gemini key (GOOGLE_API_KEY)"
)


def _unique_ids() -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return f"user-{suffix}", f"session-{suffix}"


async def _post_chat(client: httpx.AsyncClient, token: str | None, **json_body):
    headers = {}
    if token is not None:
        headers["Authorization"] = token
    return await client.post("/chat", headers=headers, json=json_body)


@pytest.fixture
async def api_client():
    transport = httpx.ASGITransport(app=api.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def fake_ecommerce_calls(monkeypatch):
    """Records every call to the Ecommerce API without touching real httpx/network.

    Patches `EcommerceClient.request` directly (a plain Python attribute swap) instead
    of using respx: respx patches httpx's transport dispatch globally, which was found
    to interfere with the real Gemini call these tests also make (empty-candidate
    responses) when both were active in the same process.
    """
    calls: list[tuple[str, str, str | None]] = []

    async def fake_request(method: str, path: str, token: str | None = None, **kwargs):
        calls.append((method, path, token))
        req = httpx.Request(method, path)
        return httpx.Response(
            200, request=req, json={"items": [], "total_count": 0, "has_next_page": False}
        )

    monkeypatch.setattr(ecommerce_client, "request", fake_request)
    return calls


async def test_missing_authorization_header_returns_422(api_client):
    """AC-CHATAPI-I01"""
    resp = await api_client.post(
        "/chat", json={"session_id": "s", "user_id": "u", "message": "oi"}
    )
    assert resp.status_code == 422


async def test_authorization_without_bearer_prefix_returns_401(api_client):
    """AC-CHATAPI-I02"""
    user_id, session_id = _unique_ids()
    resp = await _post_chat(
        api_client, "token123", session_id=session_id, user_id=user_id, message="oi"
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing bearer token"


async def test_new_session_creates_state_with_token(api_client):
    """AC-CHATAPI-I03"""
    user_id, session_id = _unique_ids()

    resp = await _post_chat(
        api_client,
        "Bearer test-token-1",
        session_id=session_id,
        user_id=user_id,
        message="oi, tudo bem?",
    )

    assert resp.status_code == 200
    assert resp.json()["reply"]

    session = await api.session_service.get_session(
        app_name=api.APP_NAME, user_id=user_id, session_id=session_id
    )
    assert session is not None
    assert session.state["access_token"] == "test-token-1"


async def test_second_turn_reuses_session_history(api_client):
    """AC-CHATAPI-I04"""
    user_id, session_id = _unique_ids()

    await _post_chat(
        api_client,
        "Bearer test-token-1",
        session_id=session_id,
        user_id=user_id,
        message="meu nome é Ana",
    )
    resp2 = await _post_chat(
        api_client,
        "Bearer test-token-1",
        session_id=session_id,
        user_id=user_id,
        message="qual é o meu nome?",
    )

    assert resp2.status_code == 200
    session = await api.session_service.get_session(
        app_name=api.APP_NAME, user_id=user_id, session_id=session_id
    )
    assert len(session.events) >= 4  # 2 user turns + 2 agent replies, at minimum


async def test_token_forwarded_to_tool_call(api_client, fake_ecommerce_calls):
    """AC-CHATAPI-I05"""
    user_id, session_id = _unique_ids()

    await _post_chat(
        api_client,
        "Bearer forwarded-token",
        session_id=session_id,
        user_id=user_id,
        message="quais sao meus pedidos?",
    )

    assert fake_ecommerce_calls, "expected the LLM to call a tool that hits the Ecommerce API"
    assert fake_ecommerce_calls[-1] == ("GET", "/api/v1/orders", "forwarded-token")


async def test_token_rotates_between_turns(api_client, fake_ecommerce_calls):
    """AC-CHATAPI-I06"""
    user_id, session_id = _unique_ids()

    await _post_chat(
        api_client,
        "Bearer token-a",
        session_id=session_id,
        user_id=user_id,
        message="oi",
    )
    await _post_chat(
        api_client,
        "Bearer token-b",
        session_id=session_id,
        user_id=user_id,
        message="quais sao meus pedidos?",
    )

    assert fake_ecommerce_calls, "expected the second turn to call a tool"
    assert fake_ecommerce_calls[-1] == ("GET", "/api/v1/orders", "token-b")
