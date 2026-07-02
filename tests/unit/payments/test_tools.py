import httpx
import respx

from alita_agent.tools import get_payment_status

TEST_BASE_URL = "http://test-ecommerce-api"


@respx.mock
async def test_get_payment_status_success_nests_under_payment(test_client, tool_context):
    """AC-PAYMENTS-U01"""
    body = {"order_id": "o1", "status": "APPROVED", "amount": 199.9}
    respx.get(f"{TEST_BASE_URL}/api/v1/payments/o1").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = await get_payment_status("o1", tool_context)

    assert result == {"status": "success", "payment": body}


@respx.mock
async def test_get_payment_status_expired_token_returns_friendly_error(
    test_client, tool_context
):
    """AC-PAYMENTS-U02"""
    respx.get(f"{TEST_BASE_URL}/api/v1/payments/o1").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    result = await get_payment_status("o1", tool_context)

    assert result == {"status": "error", "message": "Sessão expirada, faça login novamente."}
